"""Request validation for the trip API."""

from typing import Any

from rest_framework import serializers

from routing.places import PlaceNotFoundError, resolve_place
from stations.models import Place


class PlaceField(serializers.CharField):
    """A "City, ST" string resolved to a Place."""

    def to_internal_value(self, data: str) -> Place:  # type: ignore[override]
        """Resolve the text to a Place or report why it can't be."""
        text = super().to_internal_value(data)
        try:
            return resolve_place(text)
        except PlaceNotFoundError as error:
            raise serializers.ValidationError(str(error)) from error


class TripRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Start and finish of a trip, each a US place written as "City, ST"."""

    start = PlaceField(help_text='Where the trip starts, e.g. "New York, NY".')
    finish = PlaceField(help_text='Where the trip ends, e.g. "Los Angeles, CA".')

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Reject trips that start and finish in the same place."""
        if attrs["start"] == attrs["finish"]:
            raise serializers.ValidationError("Start and finish must be different places.")
        return attrs
