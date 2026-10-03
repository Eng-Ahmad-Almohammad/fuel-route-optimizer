"""URLs for the routing app."""

from django.urls import path

from routing.views import TripMapView, TripPlanView

urlpatterns = [
    path("api/route/", TripPlanView.as_view(), name="trip-plan"),
    path("map/", TripMapView.as_view(), name="trip-map"),
]
