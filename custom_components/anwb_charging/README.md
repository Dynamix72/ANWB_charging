# ANWB Fuel & Charging

Een Home Assistant custom component die zowel ANWB laadpalen als ANWB brandstofprijzen kan ophalen en tonen.

Belangrijkste features
- Laadpaal-zoekfunctie (zoals voorheen).
- Brandstofprijzen ophalen voor stations (euro95, diesel, autogas).
- Keuze welke data opgehaald wordt: chargers, fuels of beide.
- Configflow met opties voor OpenRouteService API key, data mode en brandstoftype.

Welke ANWB API wordt gebruikt
- Laadpalen: type-filter=CHARGING_LOCATION
- Brandstofstations: type-filter=FUEL_STATION

Voor brandstofstations gebruikt de integratie de ANWB POI endpoint:
https://api.anwb.nl/routing/points-of-interest/v3/all?bounding-box-filter={bbox}&type-filter=FUEL_STATION

Configuratie
- Voeg de integratie toe via Integraties (config flow). Je selecteert een device_tracker (gps) en optioneel een OpenRouteService API key.
- In de opties kun je kiezen wat je wilt ophalen (chargers/fuels/both) en welk brandstoftype je wil gebruiken.

Beschikbare entities (voorbeeld)
- sensor.anwb_cheapest_charger
- sensor.anwb_charger_count
- sensor.anwb_top_1 ... sensor.anwb_top_10
- sensor.anwb_cheapest_fuel
- sensor.anwb_fuel_count
- sensor.anwb_top_fuel_1 ... sensor.anwb_top_fuel_10

Dashboard voorbeelden
Zie dashboard_anwb_charging.yaml voor een Lovelace voorbeeld. Hieronder een korte toevoeging die fuel-sensors inschakelt bij de update-knop.

In dashboard_anwb_charging.yaml zoek naar de update-knop en voeg de fuel sensors toe aan de service_data/entity_id lijst:

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

Extra notes
- De integratie probeert route-afstanden te berekenen met OpenRouteService wanneer een bestemming is opgegeven. Geef je geen ORS API key, dan valt de integratie terug op enkel bounding-box zoeken (minder nauwkeurig voor route-detours).
- Als je problemen hebt met rate limits van ANWB, bekijk de logs; de integratie implementeert retries en backoff voor 429/5xx responses.

