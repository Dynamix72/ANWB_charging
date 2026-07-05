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

        statuses = []

        for evse in evses:
            statuses.append(
                evse.get("status")
            )

        if (
            "AVAILABLE" in statuses
            or "CHARGING" in statuses
        ):
            valid.append(charger)

    return valid


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

    async_add_entities(
        [
            CheapestChargerSensor(
                coordinator
            ),
            ChargerCountSensor(
                coordinator
            ),
        ]
    )


class CheapestChargerSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(
        self,
        coordinator,
    ):
        super().__init__(coordinator)

        self._attr_name = (
            "ANWB Cheapest Charger"
        )

        self._attr_unique_id = (
            "anwb_cheapest"
        )

    @property
    def native_value(self):

        if not self.coordinator.data:
            return "Geen data"

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        chargers = filter_valid_chargers(
            chargers
        )

        if not chargers:
            return "Geen laadpalen"

        cheapest = min(
            chargers,
            key=lambda c: float(
                c["price"]["price"]
            )
        )

        return cheapest["title"]

    @property
    def extra_state_attributes(self):

        if not self.coordinator.data:
            return {}

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        chargers = filter_valid_chargers(
            chargers
        )

        if not chargers:
            return {}

        cheapest = min(
            chargers,
            key=lambda c: float(
                c["price"]["price"]
            )
        )

        return {
            "charger_count":
                len(chargers),

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

            "latitude":
                cheapest["coordinates"]["latitude"],

            "longitude":
                cheapest["coordinates"]["longitude"],

            "charger_id":
                cheapest["id"],

            "provider":
                cheapest["title"],

            "raw_data":
                cheapest,
        }


class ChargerCountSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(
        self,
        coordinator,
    ):
        super().__init__(coordinator)

        self._attr_name = (
            "ANWB Charger Count"
        )

        self._attr_unique_id = (
            "anwb_charger_count"
        )

        self._attr_icon = (
            "mdi:ev-station"
        )

    @property
    def native_value(self):

        if not self.coordinator.data:
            return 0

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        chargers = filter_valid_chargers(
            chargers
        )

        return len(chargers)
