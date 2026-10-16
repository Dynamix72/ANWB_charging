# ANWB Charging & Fuel

Dit project verzamelt en beheert informatie over ANWB-laadpunten (EV charging) en tankstations (fuel). Het doel is data over locaties, beschikbaarheid, tarieven en integraties te centraliseren zodat mobiele en web-apps er makkelijk op kunnen bouwen.

Let op: de aanbevolen nieuwe repositorynaam is: `ANWB-charging-and-fuel`.

Features
- Locaties en metadata van laadpunten (type connector, vermogen, operator)
- Locaties en metadata van tankstations (brandstoftype, services, openingstijden)
- API / scripts om data te importeren, te normaliseren en te publiceren
- Integratievoorbeelden en CLI-tools voor analyse

Installatie
1. Clone de repository (na hernoemen: vervang NEW_NAME door de nieuwe repo-naam):

```bash
# huidige naam
git clone https://github.com/Dynamix72/ANWB_charging.git
# na hernoemen
# git clone https://github.com/Dynamix72/ANWB-charging-and-fuel.git
```

2. Maak een virtuele omgeving en installeer dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Gebruik
- Voorbeeldscripts:

```bash
python scripts/import_charging.py --source data/charging.csv
python scripts/import_fuel.py --source data/fuel.csv
```

- Plaats API-keys en configuratie in een `.env`-bestand (zorg dat `.env` in `.gitignore` staat).

Projectstructuur (voorstel)
- scripts/        — import & verwerkingsscripts
- data/           — voorbeelddata en formats
- docs/           — documentatie en specificaties
- src/            — broncode / API

Contributie
- Issues en pull requests zijn welkom. Beschrijf duidelijk wat je toevoegt en voeg tests toe waar mogelijk.
- Als je specifieke richtlijnen wilt, kan ik een CONTRIBUTING.md toevoegen.

Licentie
- Voeg hier de gewenste licentie toe (bijv. MIT). Wil je dat ik een LICENSE-bestand aanmaak, en welke licentie wil je gebruiken?

Repository hernoemen
- Ik kan de README bijwerken, maar ik kan de repository niet direct hernoemen vanuit deze interface. Hieronder staan twee manieren om te hernoemen:

1) Via GitHub UI (aanbevolen):
   Repository -> Settings -> Repository name -> vul `ANWB-charging-and-fuel` in -> Rename

2) Via de GitHub REST API (vereist een Personal Access Token met repo-permissies):

```bash
curl -X PATCH -H "Authorization: token YOUR_TOKEN" \
  -d '{"name":"ANWB-charging-and-fuel"}' \
  https://api.github.com/repos/Dynamix72/ANWB_charging
```

Contact
- Voor vragen of samenwerking: https://github.com/Dynamix72
