from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AnwbCoordinator


def filter_valid_chargers(chargers):

    valid = []

    for charger in chargers:

        if charger.get("price") is None:
            continue

        evses = charger.get(
            "electricVehicleSupplyEquipment",
            []
        )

        statuses = [
            evse.get("status")
            for evse in evses
        ]

        if (
            "AVAILABLE" in statuses
            or "CHARGING" in statuses
        ):
            valid.append(charger)

    return valid


def sorted_chargers(data):

    chargers = filter_valid_chargers(
        data.get("value", [])
    )

    return sorted(
        chargers,
        key=lambda c: float(
            c["price"]["price"]
        )
    )


def extract_charger_info(charger):

    max_power_kw = 0

    total_points = 0
    available_points = 0

    energy_price = None
    energy_display_text = []

    session_price = None
    session_display_text = []

    for evse in charger.get(
        "electricVehicleSupplyEquipment",
        []
    ):

        total_points += 1

        if evse.get("status") == "AVAILABLE":
            available_points += 1

        for connector in evse.get(
            "connectors",
            []
        ):

            max_power_kw = max(
                max_power_kw,
                connector.get(
                    "maxPowerInKW",
                    0
                )
            )

            for tariff in connector.get(
                "prices",
                []
            ):

                for component in tariff.get(
                    "priceComponents",
                    []
                ):

                    code = component.get("code")

                    if (
                        code == "ENERGY"
                        and energy_price is None
                    ):
                        energy_price = component.get(
                            "value"
                        )

                        energy_display_text = (
                            component.get(
                                "displayText",
                                []
                            )
                        )

                    if (
                        code == "SESSION"
                        and session_price is None
                    ):
                        session_price = component.get(
                            "value"
                        )

                        session_display_text = (
                            component.get(
                                "displayText",
                                []
                            )
                        )

    return {
        "max_power_kw": max_power_kw,
        "charge_points_total": total_points,
        "charge_points_available": available_points,
        "availability_text": f"{available_points}/{total_points}",
        "energy_price": energy_price,
        "energy_display_text": energy_display_text,
        "session_price": session_price,
        "session_display_text": session_display_text,
    }


async def async_setup_entry(
    hass,
    entry,
    async_add_entities,
):

    coordinator = AnwbCoordinator(
        hass,
        entry.data["device_tracker"],
        entry.data["radius"],
    )

    await coordinator.async_config_entry_first_refresh()

    entities = [
        CheapestChargerSensor(coordinator),
        ChargerCountSensor(coordinator),
    ]

    for rank in range(1, 11):

        entities.append(
            TopChargerSensor(
                coordinator,
                rank,
            )
        )

    async_add_entities(entities)


class CheapestChargerSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "ANWB Cheapest Charger"
        self._attr_unique_id = "anwb_cheapest"

    @property
    def native_value(self):

        chargers = sorted_chargers(
            self.coordinator.data
        )

        if not chargers:
            return "Geen laadpalen"

        return chargers[0]["title"]


class ChargerCountSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "ANWB Charger Count"
        self._attr_unique_id = "anwb_charger_count"
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):

        chargers = sorted_chargers(
            self.coordinator.data
        )

        return len(chargers)


class TopChargerSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(
        self,
        coordinator,
        rank,
    ):
        super().__init__(coordinator)

        self.rank = rank

        self._attr_name = (
            f"ANWB Top {rank}"
        )

        self._attr_unique_id = (
            f"anwb_top_{rank}"
        )

    def _charger(self):

        chargers = sorted_chargers(
            self.coordinator.data
        )

        index = self.rank - 1

        if len(chargers) <= index:
            return None

        return chargers[index]

    @property
    def native_value(self):

        charger = self._charger()

        if charger is None:
            return "Geen laadpaal"

        return charger["title"]

    @property
    def extra_state_attributes(self):

        charger = self._charger()

        if charger is None:
            return {}

        status = "AVAILABLE"

        for evse in charger.get(
            "electricVehicleSupplyEquipment",
            []
        ):

            if (
                evse.get("status")
                == "CHARGING"
            ):
                status = "CHARGING"
                break

        info = extract_charger_info(
            charger
        )

        return {

            "rank": self.rank,

            "price_per_kwh":
                info["energy_price"],

            "price_display_text":
                info["energy_display_text"],

            "session_price":
                info["session_price"],

            "session_display_text":
                info["session_display_text"],

            "max_power_kw":
                info["max_power_kw"],

            "charge_points_total":
                info["charge_points_total"],

            "charge_points_available":
                info["charge_points_available"],

            "availability_text":
                info["availability_text"],

            "currency":
                charger["price"]["currency"],

            "street":
                charger["address"][
                    "streetAddress"
                ],

            "postal_code":
                charger["address"][
                    "postalCode"
                ],

            "city":
                charger["address"][
                    "city"
                ],

            "full_address":
                f"{charger['address']['streetAddress']}, "
                f"{charger['address']['postalCode']} "
                f"{charger['address']['city']}",

            "status":
                status,

            "icon":
                "mdi:lightning-bolt"
                if status == "CHARGING"
                else "mdi:ev-station",

            "latitude":
                charger["coordinates"][
                    "latitude"
                ],

            "longitude":
                charger["coordinates"][
                    "longitude"
                ],
        }
