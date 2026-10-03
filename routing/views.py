"""Trip planning API and the map page that displays its result."""

from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.client import NoRouteError, RoutingServiceError
from routing.optimizer import InfeasibleTripError
from routing.planner import plan_trip
from routing.serializers import TripRequestSerializer
from stations.models import Place


class TripPlanView(APIView):
    """Plan a trip between two US places: the route, the cheapest fuel stops and the total fuel cost.

    Send `start` and `finish` as "City, ST", in a JSON body (POST) or as query parameters (GET).
    """

    def get(self, request: Request) -> Response:
        """Plan a trip from query parameters."""
        return self._plan(request, request.query_params)

    def post(self, request: Request) -> Response:
        """Plan a trip from a JSON body."""
        return self._plan(request, request.data)

    def _plan(self, request: Request, data: object) -> Response:
        serializer = TripRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        start: Place = serializer.validated_data["start"]
        finish: Place = serializer.validated_data["finish"]
        cache_key = f"trip:{start.key}:{start.state}:{finish.key}:{finish.state}"
        plan = cache.get(cache_key)
        cached = plan is not None
        if plan is None:
            try:
                plan = plan_trip(start, finish)
            except (NoRouteError, InfeasibleTripError) as error:
                return Response({"detail": str(error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except RoutingServiceError as error:
                return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
            cache.set(cache_key, plan, settings.TRIP_CACHE_SECONDS)
        map_query = urlencode({"start": str(start), "finish": str(finish)})
        map_url = request.build_absolute_uri(f"{reverse('trip-map')}?{map_query}")
        return Response({**plan, "cached": cached, "map_url": map_url})


class TripMapView(TemplateView):
    """A Leaflet map that calls the trip API and draws the route and fuel stops."""

    template_name = "routing/map.html"
