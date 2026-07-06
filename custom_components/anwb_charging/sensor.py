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

    @property
    def extra_state_attributes(self):

        chargers = sorted_chargers(
            self.coordinator.data
        )

        if not chargers:
            return {}

        cheapest = chargers[0]

        return {
            "price_per_kwh":
                cheapest["price"]["price"],
            "currency":
                cheapest["price"]["currency"],
            "street":
                cheapest["address"]["streetAddress"],
            "postal_code":
                cheapest["address"]["postalCode"],
            "city":
                cheapest["address"]["city"],
            "full_address":
                f"{cheapest['address']['streetAddress']}, "
                f"{cheapest['address']['postalCode']} "
                f"{cheapest['address']['city']}",
            "latitude":
                cheapest["coordinates"]["latitude"],
            "longitude":
                cheapest["coordinates"]["longitude"],
        }


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

        return {
            "rank": self.rank,

            "price_per_kwh":
                charger["price"]["price"],

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

            "latitude":
                charger["coordinates"][
                    "latitude"
                ],

            "longitude":
                charger["coordinates"][
                    "longitude"
                ],
        }
