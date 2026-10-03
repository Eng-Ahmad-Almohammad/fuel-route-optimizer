"""Choose where to buy fuel along a route so the trip costs as little as possible.

Once every station has a mile marker the map no longer matters: this is the "gas station problem" on a line.
The planner minimizes ``fuel cost + stop_cost x number of stops``. With ``stop_cost = 0`` that is the cheapest
possible fuel bill, but the plan then stops for a gallon here and there to save cents; a small stop cost (the
driver's time) removes those stops for a fraction of a percent more fuel.

It is a dynamic program over the structure of optimal plans (Khuller, Malekian and Mestre, "To fill or not to
fill: the gas station problem", 2007): between two consecutive stops u and v, an optimal plan either

* fills the tank at u, when u is cheaper than v, or
* buys just enough at u to reach v with an empty tank, when v is at least as cheap.

So the vehicle reaches a stop either empty or with what is left of a full tank bought at an earlier stop, which
keeps the number of states small. Fuel is tracked in miles of driving; gallons are miles / miles per gallon.

The tank starts empty and the first stop is any station within ``start_radius_miles`` of the start (always
including the first station on the route). The miles driven to reach it are billed at its price, so the plan
pays for every mile driven.
"""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


class InfeasibleTripError(Exception):
    """Some stretch of the route is longer than a full tank with no station on it."""

    def __init__(self, gap_start_mile: float, range_miles: float) -> None:
        """Record where the vehicle would run out of fuel."""
        super().__init__(gap_start_mile, range_miles)
        self.gap_start_mile = gap_start_mile
        self.range_miles = range_miles

    def __str__(self) -> str:
        return (
            f"No fuel station within {self.range_miles:g} miles after mile {self.gap_start_mile:.0f}; "
            "the vehicle cannot complete this trip."
        )


@dataclass(frozen=True)
class StationStop:
    """A station on the route: its mile marker and price per gallon."""

    mile: float
    price: float


@dataclass(frozen=True)
class Purchase:
    """Fuel bought at ``stations[station_index]``."""

    station_index: int
    gallons: float
    cost: float


@dataclass(frozen=True)
class _Arrival:
    """Arriving at ``stations[index]``: empty, or with what is left of a full tank bought at ``filled_at``."""

    index: int
    filled_at: int | None


# How an arrival was reached: the previous arrival and the miles of fuel bought there.
_Step = tuple[_Arrival, float]


def plan_purchases(
    stations: Sequence[StationStop],
    total_miles: float,
    range_miles: float,
    miles_per_gallon: float,
    stop_cost: float = 0.0,
    start_radius_miles: float = 0.0,
) -> list[Purchase]:
    """Return the purchases that get the vehicle from mile 0 to ``total_miles`` at the lowest total cost.

    ``stations`` must be sorted by mile, at distinct miles, within the route.

    >>> stops = [StationStop(0, 3.50), StationStop(180, 3.10), StationStop(420, 3.60), StationStop(610, 2.90),
    ...          StationStop(900, 3.40), StationStop(1050, 3.20)]
    >>> plan = plan_purchases(stops, total_miles=1400, range_miles=500, miles_per_gallon=10)
    >>> [(p.station_index, round(p.gallons, 2), round(p.cost, 2)) for p in plan]
    [(0, 18.0, 63.0), (1, 43.0, 133.3), (3, 50.0, 145.0), (5, 29.0, 92.8)]
    """
    _check_reachable(stations, total_miles, range_miles)
    planner = _Planner(stations, total_miles, range_miles, miles_per_gallon, stop_cost)
    return planner.solve(start_radius_miles)


def _check_reachable(stations: Sequence[StationStop], total_miles: float, range_miles: float) -> None:
    if not stations:
        raise InfeasibleTripError(0.0, range_miles)
    previous = 0.0
    for mile in [*(stop.mile for stop in stations), total_miles]:
        if mile - previous > range_miles:
            raise InfeasibleTripError(previous, range_miles)
        previous = mile


class _Planner:
    def __init__(
        self,
        stations: Sequence[StationStop],
        total_miles: float,
        range_miles: float,
        miles_per_gallon: float,
        stop_cost: float,
    ) -> None:
        self.stations = stations
        self.total_miles = total_miles
        self.range_miles = range_miles
        self.miles_per_gallon = miles_per_gallon
        self.stop_cost = stop_cost
        self.best: dict[_Arrival, float] = {}
        self.came_from: dict[_Arrival, _Step | None] = {}
        self.pending: dict[int, list[_Arrival]] = defaultdict(list)
        self.finish_cost = math.inf
        self.finish_from: _Step | None = None

    def solve(self, start_radius_miles: float) -> list[Purchase]:
        self._add_first_stops(start_radius_miles)
        for index in range(len(self.stations)):
            for arrival in self.pending[index]:
                self._try_finish(arrival)
                for target in self._reachable_from(index):
                    self._try_leg(arrival, target)
        if self.finish_from is None:  # pragma: no cover - _check_reachable guarantees a plan exists
            raise InfeasibleTripError(0.0, self.range_miles)
        return self._purchases(self.finish_from)

    def _add_first_stops(self, start_radius_miles: float) -> None:
        """The tank starts empty: any station near the start can be the first stop, paying for the miles to it."""
        first_stop_limit = min(max(start_radius_miles, self.stations[0].mile), self.range_miles)
        for index, stop in enumerate(self.stations):
            if stop.mile <= first_stop_limit:
                self._reach(_Arrival(index, None), self._price(index, stop.mile), None)

    def _price(self, index: int, fuel_miles: float) -> float:
        return fuel_miles / self.miles_per_gallon * self.stations[index].price

    def _fuel_on_arrival(self, arrival: _Arrival) -> float:
        if arrival.filled_at is None:
            return 0.0
        return self.range_miles - (self.stations[arrival.index].mile - self.stations[arrival.filled_at].mile)

    def _reachable_from(self, index: int) -> range:
        end = index + 1
        while end < len(self.stations) and self.stations[end].mile - self.stations[index].mile <= self.range_miles:
            end += 1
        return range(index + 1, end)

    def _reach(self, arrival: _Arrival, cost: float, step: _Step | None) -> None:
        if cost >= self.best.get(arrival, math.inf):
            return
        if arrival not in self.best:
            self.pending[arrival.index].append(arrival)
        self.best[arrival] = cost
        self.came_from[arrival] = step

    def _try_leg(self, arrival: _Arrival, target: int) -> None:
        """Stop at ``arrival.index`` and drive to ``target`` as the next stop."""
        here = arrival.index
        leg = self.stations[target].mile - self.stations[here].mile
        fuel = self._fuel_on_arrival(arrival)
        if self.stations[here].price < self.stations[target].price:
            bought, next_arrival = self.range_miles - fuel, _Arrival(target, here)
        elif fuel < leg:
            bought, next_arrival = leg - fuel, _Arrival(target, None)
        else:
            return  # enough fuel to pass this station; the leg from the earlier fill-up covers it
        cost = self.best[arrival] + self._price(here, bought) + self.stop_cost
        self._reach(next_arrival, cost, (arrival, bought))

    def _try_finish(self, arrival: _Arrival) -> None:
        leg = self.total_miles - self.stations[arrival.index].mile
        if leg > self.range_miles:
            return
        bought = max(0.0, leg - self._fuel_on_arrival(arrival))
        cost = self.best[arrival] + self._price(arrival.index, bought) + (self.stop_cost if bought else 0.0)
        if cost < self.finish_cost:
            self.finish_cost, self.finish_from = cost, (arrival, bought)

    def _purchases(self, last_step: _Step) -> list[Purchase]:
        fuel_miles: dict[int, float] = defaultdict(float)
        step: _Step | None = last_step
        first = last_step[0]
        while step is not None:
            arrival, bought = step
            fuel_miles[arrival.index] += bought
            first, step = arrival, self.came_from[arrival]
        fuel_miles[first.index] += self.stations[first.index].mile  # miles driven before the first stop
        return [
            Purchase(index, miles / self.miles_per_gallon, self._price(index, miles))
            for index, miles in sorted(fuel_miles.items())
            if miles > 0
        ]
