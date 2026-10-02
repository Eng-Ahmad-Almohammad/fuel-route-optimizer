"""Admin registrations for the stations app."""

from django.contrib import admin

from stations.models import FuelStation, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for gazetteer places."""

    list_display = ["name", "state", "latitude", "longitude"]
    list_filter = ["state"]
    search_fields = ["name", "key"]


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for truck stops and their fuel prices."""

    list_display = ["opis_id", "name", "city", "state", "price"]
    list_filter = ["state"]
    search_fields = ["name", "city"]
    ordering = ["price"]
