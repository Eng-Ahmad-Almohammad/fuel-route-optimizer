# Data files

| File | What it is | Source |
| --- | --- | --- |
| `fuel-prices-for-be-assessment.csv` | Truck stops with their retail fuel price (USD/gallon). | Provided with the assignment, cleaned: trimmed whitespace, dropped Canadian rows, merged duplicate `OPIS Truckstop ID` rows keeping the lowest price. |
| `census/2025_Gaz_place_national.zip` | Coordinates of every US incorporated place and CDP. | [US Census Gazetteer Files](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html) |
| `census/2025_Gaz_cousubs_national.zip` | Coordinates of US county subdivisions (townships such as Mahwah, NJ). | Same as above |
| `place_overrides.csv` | Coordinates for the 131 truck stop cities that the Census files do not list (unincorporated communities such as Ruther Glen, VA). | OpenStreetMap Nominatim, generated once by `python manage.py geocode_missing_places` |

## How they are used

The price list has no coordinates and its addresses are highway exits (`I-44, EXIT 283 & US-69`), so each truck
stop is placed at the coordinates of its city. `python manage.py load_fuel_data` builds a place index from the
Census files plus the overrides, stores it in the `Place` table and stores every truck stop in the `FuelStation`
table with its city's coordinates. The same `Place` table resolves the "City, ST" inputs of the API, so no geocoding
API is called while serving requests.

`geocode_missing_places` only needs to be re-run if the price list changes and adds cities the Census files don't
know. It appends to `place_overrides.csv` and respects Nominatim's limit of one request per second.
