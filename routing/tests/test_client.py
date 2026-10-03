"""Tests for the OpenRouteService client."""

import re
from unittest.mock import MagicMock

import pytest
import requests
from pytest_mock import MockerFixture

from routing.client import NoRouteError, RoutingServiceError, fetch_route


def response(status: int, payload: object = None, text: str = "") -> MagicMock:
    mock = MagicMock(status_code=status, ok=status < 400, text=text)
    if payload is None:
        mock.json.side_effect = ValueError("not JSON")
    else:
        mock.json.return_value = payload
    return mock


ROUTE_PAYLOAD = {
    "features": [
        {
            "geometry": {"type": "LineString", "coordinates": [[-95.99, 36.15], [-94.58, 39.10]]},
            "properties": {"summary": {"distance": 248.4, "duration": 13200.0}},
        },
    ],
}


def test_fetch_route_sends_one_request_and_parses_the_route(mocker: MockerFixture) -> None:
    post = mocker.patch("routing.client.requests.post", return_value=response(200, ROUTE_PAYLOAD))

    route = fetch_route((-95.99, 36.15), (-94.58, 39.10))

    assert route.coordinates == [(-95.99, 36.15), (-94.58, 39.10)]
    assert route.distance_miles == 248.4
    assert post.call_count == 1
    assert post.call_args.kwargs["json"]["coordinates"] == [[-95.99, 36.15], [-94.58, 39.10]]
    assert post.call_args.kwargs["json"]["units"] == "mi"
    assert post.call_args.kwargs["headers"] == {"Authorization": "test-openrouteservice-key"}


def test_no_route_found(mocker: MockerFixture) -> None:
    payload = {"error": {"code": 2010, "message": "Could not find routable point"}}
    mocker.patch("routing.client.requests.post", return_value=response(404, payload))

    with pytest.raises(NoRouteError, match="Could not find routable point"):
        fetch_route((0, 0), (1, 1))


@pytest.mark.parametrize(
    ("status", "payload", "text", "message"),
    [
        (403, {"error": "Access to this API has been disallowed"}, "", "403: Access to this API"),
        (429, {"error": {"code": 429}}, "", "429: {'code': 429}"),
        (500, None, "<html>Server error</html>", "500: <html>Server error"),
        (502, ["unexpected"], "", "502: ['unexpected']"),
    ],
)
def test_service_errors(mocker: MockerFixture, status: int, payload: object, text: str, message: str) -> None:
    mocker.patch("routing.client.requests.post", return_value=response(status, payload, text))

    with pytest.raises(RoutingServiceError, match=re.escape(message)):
        fetch_route((0, 0), (1, 1))


def test_network_failure(mocker: MockerFixture) -> None:
    mocker.patch("routing.client.requests.post", side_effect=requests.ConnectionError("timed out"))

    with pytest.raises(RoutingServiceError, match="Could not reach the routing service"):
        fetch_route((0, 0), (1, 1))
