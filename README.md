# ANWB Charging & Fuel

This project collects and manages information about ANWB charging locations (EV charging) and fuel stations. The goal is to centralize data about locations, availability, pricing, and integrations.

Features
- Locations and metadata for charging stations (connector types, power, operator)
- Locations and metadata for fuel stations (fuel types, services, opening hours)
- Scripts and APIs to import, normalize, and publish data
- Integration examples and CLI tools for analysis

Installation
1. Clone the repository (after rename: replace NEW_NAME with the new repository name):

```bash
# current name
git clone https://github.com/Dynamix72/ANWB_charging.git
# after rename
# git clone https://github.com/Dynamix72/ANWB-charging-and-fuel.git
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Usage
- Example scripts:

```bash
python scripts/import_charging.py --source data/charging.csv
python scripts/import_fuel.py --source data/fuel.csv
```

- Place API keys and configuration in a `.env` file (ensure `.env` is listed in `.gitignore`).

Project structure (suggested)
- scripts/        — import & processing scripts
- data/           — sample data and formats
- docs/           — documentation and specifications
- src/            — source code / API

Contributing
- Issues and pull requests are welcome. Please describe your changes clearly and add tests where applicable.
- If you want contributor guidelines, I can add a CONTRIBUTING.md.

License
- Add your preferred license here (e.g., MIT). Do you want me to add a LICENSE file, and if so, which license should I use?

Repository rename
- I can update the README, but I cannot rename the repository from this interface. Below are two ways to rename it:

1) Via the GitHub UI (recommended):
   Repository -> Settings -> Repository name -> enter `ANWB-charging-and-fuel` -> Rename

2) Via the GitHub REST API (requires a Personal Access Token with repo permissions):

```bash
curl -X PATCH -H "Authorization: token YOUR_TOKEN" \
  -d '{"name":"ANWB-charging-and-fuel"}' \
  https://api.github.com/repos/Dynamix72/ANWB_charging
```

Contact
- For questions or collaboration: https://github.com/Dynamix72
