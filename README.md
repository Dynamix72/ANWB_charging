# ANWB Charging Integration

Home Assistant integratie voor ANWB Laadpalen - vind de goedkoopste laadpalen op je route!

## Beschrijving

Deze integratie helpt je om de goedkoopste beschikbare laadpalen te vinden rekening houdend met:
- **Prijs** - Goedkoopste laadpalen eerst
- **Locatie** - Laadpalen in je buurt (10 km radius vast ingesteld)
- **Route** - Laadpalen op of vlak bij je route naar een bestemming
- **Omrijafstand** - Maximale extra kilometers die je wilt rijden (instelbaar)
- **Ladertype** - Filtert op AC laders, Snelladers, Ultrasnelladers of alle typen

## Installatie

### Via HACS (aanbevolen)
1. Open HACS in Home Assistant
2. Ga naar "Integrations"
3. Klik op "Explore & Download Repositories"
4. Zoek naar "ANWB Charging"
5. Klik "Download"
6. Herstart Home Assistant

### Handmatig
1. Clone of download deze repository
2. Kopieer `custom_components/anwb_charging` naar je Home Assistant `custom_components` directory
3. Herstart Home Assistant

## Configuratie

### Stap 1: Voeg de integratie toe
1. Ga naar Settings → Devices & Services → Integrations
2. Klik op "Create Integration"
3. Zoek naar "ANWB Charging"
4. Klik op de integratie

### Stap 2: Configureer de instellingen

Bij eerste setup moet je invullen:

#### **Device Tracker (Verplicht)**
Dit is je GPS bron. Je kunt kiezen uit:
- Telefoon GPS (b.v. `device_tracker.mijn_telefoon`)
- Auto GPS
- Ander apparaat met GPS

> ℹ️ Voorkeur: Kies een stabiele GPS bron, niet de iPhone default (te veel ruis)

#### **Bestemming (Verplicht)**
Waar wil je heen? Bijv:
- `Amsterdam`
- `Schiphol Airport`
- `Maastricht`
- Volledig adres: `Kalverstraat 12, Amsterdam`

#### **Maximale Omrijafstand (Verplicht)**
Hoeveel extra kilometers wil je rijden voor een goedkopere laadpaal?
- Min: 1 km
- Max: 100 km
- Default: 10 km

Voorbeeld: 
- Route is 100 km
- Directe kosten: €8
- Laadpaal met 5 km omrijden kost: €6
- Laadpaal met 15 km omrijden kost: €4

Bij max omrijden van 10 km, zie je alleen de eerste twee opties.

#### **Ladertype (Verplicht)**
Welk type laadpaal wil je gebruiken?

| Type | Vermogen | Laadtijd |
|------|----------|----------|
| **AC laders** | < 50 kW | 1-2 uur |
| **Snelladers** | 50-150 kW | 20-45 min |
| **Ultrasnelladers** | ≥ 150 kW | 10-20 min |
| **Alle laders** | Alles | Alles |

#### **OpenRouteService API Key (Optioneel)**
Voor betere routeberekening. Gratis account met 2500 requests/maand:
1. Ga naar https://openrouteservice.org
2. Maak gratis account aan
3. Genereer API key
4. Voer key in (optioneel - werkt ook zonder)

### Stap 3: Wissel instellingen

Na setup kun je de instellingen wijzigen:
1. Ga naar Settings → Devices & Services → Integrations
2. Zoek "ANWB Charging"
3. Klik op de integratie
4. Klik op "Opties" (of het tandwiel icoon)
5. Wijzig één of meer instellingen:
   - Bestemming
   - Maximale omrijafstand
   - Ladertype
   - API Key

## Gebruik

### Handmatig API aanroepen (Knopdruk)

De integratie roept de APIs ALLEEN aan als jij dit aangeeft. Dit voorkomt oneindige API calls.

#### Via Service Call (Automations/Scripts)
```yaml
service: homeassistant.update_entity
data:
  entity_id:
    - sensor.anwb_cheapest_charger
    - sensor.anwb_charger_count
    - sensor.anwb_top_1
    - sensor.anwb_top_2
    - sensor.anwb_top_3
    - sensor.anwb_top_4
    - sensor.anwb_top_5
```

#### Via Developer Tools
1. Ga naar Developer Tools → Services
2. Service: `homeassistant.update_entity`
3. Voer entity ID in (bijv `sensor.anwb_cheapest_charger`)
4. Klik "Call Service"

### Beschikbare Sensors

Na setup krijg je deze sensors:

| Sensor | Beschrijving | Voorbeeld |
|--------|-------------|----------|
| `sensor.anwb_cheapest_charger` | Goedkoopste laadpaal title | "Albert Cuyp, Amsterdam" |
| `sensor.anwb_charger_count` | Totaal beschikbare laadpalen | 12 |
| `sensor.anwb_top_1` | #1 goedkoopste | "Station Zuid, Amsterdam" |
| `sensor.anwb_top_2` | #2 goedkoopste | "Zuidas, Amsterdam" |
| ... | ... | ... |
| `sensor.anwb_top_10` | #10 goedkoopste | "De Pijp, Amsterdam" |

### Sensor Attributen

Elke sensor bevat informatie in attributen:

```yaml
sensor.anwb_top_1:
  state: "Albert Cuyp, Amsterdam"
  attributes:
    price_per_kwh: 0.35
    max_power_kw: 150
    charge_points_available: 2
    charge_points_total: 4
    street: "Albert Cuyp"
    postal_code: "1072 SL"
    city: "Amsterdam"
    latitude: 52.3596
    longitude: 4.8950
    status: "AVAILABLE"
    detour_km: 2.3        # Omrijafstand
    extra_minutes: 8      # Extra tijd
```

## Geavanceerd Gebruik

### Automation Voorbeeld: Notificatie bij Goedkope Laadpaal

```yaml
automation:
  - alias: "Goedkope laadpaal gevonden"
    trigger:
      - platform: numeric_state
        entity_id: sensor.anwb_cheapest_charger_price_per_kwh
        below: 0.30
    action:
      - service: notify.notify
        data:
          title: "Laadpaal alert!"
          message: "Goedkope laadpaal gevonden: {{ state_attr('sensor.anwb_top_1', 'price_per_kwh') }} €/kWh"
```

### Script Voorbeeld: Update en Notificeer

```yaml
script:
  check_laadpalen:
    sequence:
      # Update alle sensors
      - service: homeassistant.update_entity
        data:
          entity_id:
            - sensor.anwb_cheapest_charger
            - sensor.anwb_charger_count
      
      # Wacht op update
      - delay: "00:00:05"
      
      # Stuur notificatie
      - service: notify.notify
        data:
          title: "Laadpalen info"
          message: |
            Aantal beschikbaar: {{ states('sensor.anwb_charger_count') }}
            Goedkoopste: {{ states('sensor.anwb_cheapest_charger') }}
            Prijs: {{ state_attr('sensor.anwb_top_1', 'price_per_kwh') }} €/kWh
```

## Troubleshooting

### "Tracker niet gevonden"
- Zorg dat je device tracker ID klopt
- Controleer of je telefoon/apparaat online is
- Check in Developer Tools → States of de tracker aanwezig is

### "Geen bestemming ingevuld"
- Voer een bestemming in via Opties
- Controleer spelling (bijv "Amsterdam" niet "amstardam")

### "Geen laadpalen gevonden"
- Controleer of laadpalen in de buurt beschikbaar zijn
- Verlaag de "Maximale omrijafstand"
- Wijzig het "Ladertype"

### API Rate Limit (429 error)
- Zorg dat je niet te veel updates aanroept
- Gebruik een script met delays tussen aanroepen
- Voeg OpenRouteService API key toe voor betere routing

## Versiegeschiedenis

### v1.1.0 (Huidige)
- ✨ Route-aware laadpaalfiltering
- ✨ Bestemming instelbaar via UI
- ✨ Maximale omrijafstand instelbaar (1-100 km)
- ✨ Ladertype selecteerbaar (AC/Snellader/Ultrasnellader/Alle)
- ✨ Alleen handmatige API calls via knopdruk
- 📝 Uitgebreide code comments

### v1.0.23
- Initiële release
- Basislaadpaal zoeken op locatie

## Licentie

MIT License

## Ondersteuning

Vragen of problemen?
1. Check de [GitHub Issues](https://github.com/Dynamix72/ANWB_charging/issues)
2. Maak een nieuwe Issue aan met details
3. Include logs uit Home Assistant

## Credits

- ANWB API voor laadpalen data
- OpenRouteService voor routeberekening
- Home Assistant community
