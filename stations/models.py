"""Models for US places and the truck stops that sell fuel."""

from django.db import models


class Place(models.Model):
    """A US city/town with coordinates, used to locate truck stops and to resolve "City, ST" inputs."""

    key = models.CharField(max_length=128, help_text="Normalized name, see gazetteer.normalize_place_name.")
    state = models.CharField(max_length=2)
    name = models.CharField(max_length=128)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "state"], name="unique_place_key_state")]

    def __str__(self) -> str:
        return f"{self.name}, {self.state}"


class FuelStation(models.Model):
    """A truck stop from the OPIS fuel price list, located at its city's coordinates."""

    opis_id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=128)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2)
    rack_id = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=8, help_text="Retail price in USD per gallon.")
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["latitude", "longitude"], name="station_lat_lon_idx")]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state}) ${self.price}"
