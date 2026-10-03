"""Tests for the fuel stop optimizer, checked against an exhaustive search on small random trips."""

import math
import random

import pytest

from routing.optimizer import InfeasibleTripError, StationStop, plan_purchases

PRICES = [2.9, 3.0, 3.1, 3.2, 3.5, 3.8]


def brute_force_cost(
    stations: list[StationStop],
    total: int,
    range_miles: int,
    stop_cost: float,
    start_radius: float,
) -> float:
    """Cheapest fuel cost + stop costs, trying every whole-mile purchase at every station (miles per gallon = 1)."""
    first_stop_limit = min(max(start_radius, stations[0].mile), range_miles)
    best = math.inf
    for first, start in enumerate(stations):
        if start.mile > first_stop_limit:
            break
        # cost_by_fuel[f] = cheapest cost to be at the current station with f miles of fuel, before buying.
        cost_by_fuel = [math.inf] * (range_miles + 1)
        cost_by_fuel[0] = start.mile * start.price
        for index in range(first, len(stations)):
            next_mile = stations[index + 1].mile if index + 1 < len(stations) else total
            # The first station always counts as a stop: the miles driven to reach it are billed there.
            cost_by_fuel = _drive_leg(
                cost_by_fuel,
                stations[index].price,
                int(next_mile - stations[index].mile),
                stop_cost,
                always_stop=index == first,
            )
        best = min(best, *cost_by_fuel)
    return best


def _drive_leg(cost_by_fuel: list[float], price: float, leg: int, stop_cost: float, always_stop: bool) -> list[float]:
    """Try every purchase at a station, then drive ``leg`` miles to the next one."""
    next_cost = [math.inf] * len(cost_by_fuel)
    for fuel, cost in enumerate(cost_by_fuel):
        for bought in range(max(0, leg - fuel), len(cost_by_fuel) - fuel):
            total_cost = cost + bought * price + (stop_cost if bought > 0 or always_stop else 0)
            next_cost[fuel + bought - leg] = min(next_cost[fuel + bought - leg], total_cost)
    return next_cost


def random_trip(rng: random.Random) -> tuple[list[StationStop], int, int]:
    range_miles, total = rng.randint(5, 25), rng.randint(10, 90)
    miles = sorted(rng.sample(range(total), rng.randint(1, min(10, total))))
    return [StationStop(mile, rng.choice(PRICES)) for mile in miles], total, range_miles


@pytest.mark.parametrize(("stop_cost", "start_radius"), [(0.0, 0.0), (0.0, 6.0), (4.0, 0.0), (4.0, 6.0)])
def test_plan_matches_exhaustive_search(stop_cost: float, start_radius: float) -> None:
    rng = random.Random(42)
    trips = [random_trip(rng) for _ in range(400)]
    feasible = [trip for trip in trips if brute_force_cost(*trip, stop_cost, start_radius) < math.inf]
    for stations, total, range_miles in trips:
        expected = brute_force_cost(stations, total, range_miles, stop_cost, start_radius)
        if expected == math.inf:
            with pytest.raises(InfeasibleTripError):
                plan_purchases(stations, total, range_miles, 1, stop_cost, start_radius)
            continue
        plan = plan_purchases(stations, total, range_miles, 1, stop_cost, start_radius)
        assert sum(purchase.cost for purchase in plan) + stop_cost * len(plan) == pytest.approx(expected)
        assert sum(purchase.gallons for purchase in plan) == pytest.approx(total)
    assert len(feasible) > 100


def test_stop_cost_skips_small_top_ups() -> None:
    # Station 1 is a hair cheaper than station 0, so without a stop cost the plan stops there for it.
    stations = [StationStop(0, 3.00), StationStop(2, 2.99), StationStop(300, 3.50)]

    cheapest = plan_purchases(stations, 450, 500, 10)
    with_stop_cost = plan_purchases(stations, 450, 500, 10, stop_cost=5.0)

    assert [purchase.station_index for purchase in cheapest] == [0, 1]
    assert [purchase.station_index for purchase in with_stop_cost] == [0]


def test_start_radius_lets_the_first_stop_be_a_cheaper_nearby_station() -> None:
    stations = [StationStop(3, 3.80), StationStop(12, 3.00)]

    plan = plan_purchases(stations, 100, 500, 10, start_radius_miles=25)

    assert [(purchase.station_index, purchase.gallons) for purchase in plan] == [(1, 10.0)]


@pytest.mark.parametrize(
    ("stations", "gap_start"),
    [
        ([], 0),
        ([StationStop(600, 3.0)], 0),
        ([StationStop(0, 3.0), StationStop(450, 3.0)], 450),
    ],
)
def test_gaps_longer_than_a_tank_are_infeasible(stations: list[StationStop], gap_start: float) -> None:
    with pytest.raises(InfeasibleTripError) as error:
        plan_purchases(stations, 1000, 500, 10)

    assert error.value.gap_start_mile == gap_start
    assert (
        str(error.value)
        == f"No fuel station within 500 miles after mile {gap_start}; the vehicle cannot complete this trip."
    )
