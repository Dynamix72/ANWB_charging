# ANWB Fuel & Charging

A Home Assistant custom component that fetches and exposes both ANWB charging stations and ANWB fuel prices.

Key features
- Charging station search (as before).
- Retrieve fuel prices for stations (Euro95, Diesel, Autogas).
- Select which data to fetch: chargers, fuels, or both.
- Config flow with options for an OpenRouteService API key, data mode, and fuel type.

Which ANWB API is used
- Charging stations: type-filter=CHARGING_LOCATION
- Fuel stations: type-filter=FUEL_STATION

For fuel stations the integration uses the ANWB POI endpoint:
https://api.anwb.nl/routing/points-of-interest/v3/all?bounding-box-filter={bbox}&type-filter=FUEL_STATION

Configuration
- Add the integration through Integrations (config flow). You select a device_tracker (GPS) and optionally provide an OpenRouteService API key.
- In the options you can choose what to fetch (chargers/fuels/both) and which fuel type to use.

Available entities (examples)
- sensor.anwb_cheapest_charger
- sensor.anwb_charger_count
- sensor.anwb_top_1 ... sensor.anwb_top_10
- sensor.anwb_cheapest_fuel
- sensor.anwb_fuel_count
- sensor.anwb_top_fuel_1 ... sensor.anwb_top_fuel_10

Examples

Config flow (UI)
- When you add the integration under Settings → Devices & Services, you'll be prompted to:
  - Select a device_tracker/entity that represents your location (GPS).
  - Optionally enter an OpenRouteService (ORS) API key to enable route-distance calculations.
  - Choose Data Mode: `chargers`, `fuels`, or `both`.
  - Choose Fuel Type: `euro95`, `diesel`, or `autogas` (only shown when `fuels` or `both` is selected).

Note: The integration uses the UI config flow; manual YAML configuration is not required.

Environment (.env) example

Create a `.env` in the repository or the environment where you run scripts (do NOT commit this file):

OPENROUTESERVICE_API_KEY=your_ors_api_key_here
ANWB_API_TIMEOUT=10

Lovelace dashboard example

Below is a Lovelace button card example showing an update action that refreshes both charger and fuel sensors. Add this to your Lovelace dashboard or include it in `dashboard_anwb_charging.yaml`.

type: button
name: Update ANWB data
tap_action:
  action: call-service
  service: homeassistant.update_entity
  service_data:
    entity_id:
      - sensor.anwb_cheapest_charger
      - sensor.anwb_charger_count
      - sensor.anwb_cheapest_fuel
      - sensor.anwb_fuel_count
      - sensor.anwb_top_1
      - sensor.anwb_top_2
      - sensor.anwb_top_3
      - sensor.anwb_top_4
      - sensor.anwb_top_5
      - sensor.anwb_top_6
      - sensor.anwb_top_7
      - sensor.anwb_top_8
      - sensor.anwb_top_9
      - sensor.anwb_top_10
      - sensor.anwb_top_fuel_1
      - sensor.anwb_top_fuel_2
      - sensor.anwb_top_fuel_3
      - sensor.anwb_top_fuel_4
      - sensor.anwb_top_fuel_5
      - sensor.anwb_top_fuel_6
      - sensor.anwb_top_fuel_7
      - sensor.anwb_top_fuel_8
      - sensor.anwb_top_fuel_9
      - sensor.anwb_top_fuel_10

Service call examples

- Update a single sensor via Developer Tools → Services:
  Service: `homeassistant.update_entity`
  Entity: `sensor.anwb_cheapest_fuel`

- Trigger a full integration update (if the integration exposes a custom update service) — check integration services after installation.

Notes
- The integration attempts to calculate route distances using OpenRouteService when a destination is provided. If you do not supply an ORS API key, the integration falls back to bounding-box searches only.
- If you experience rate limit issues with ANWB, check the logs; the integration implements retries and exponential backoff for 429 and 5xx responses.

Repository
- The repository has been renamed to `ANWB-charging-and-fuel`. When referencing the repo in documentation or example scripts, use the new clone URL:

```bash
git clone https://github.com/Dynamix72/ANWB-charging-and-fuel.git
```
