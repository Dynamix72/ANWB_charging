from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AnwbCoordinator


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
            CheapestChargerSensor(coordinator),
            ChargerCountSensor(coordinator),
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

        self._attr_name = "ANWB Cheapest Charger"
        self._attr_unique_id = "anwb_cheapest"

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def native_value(self):

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        if not chargers:
            return "Geen laadpalen"

        cheapest = min(
            chargers,
            key=lambda c: float(
                c.get("price", {}).get(
                    "price",
                    999
                )
            )
        )

        return cheapest.get(
            "title",
            "Onbekend"
        )

    @property
    def extra_state_attributes(self):

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        if not chargers:
            return {}

        cheapest = min(
            chargers,
            key=lambda c: float(
                c.get("price", {}).get(
                    "price",
                    999
                )
            )
        )

        return {
            "charger_count": len(chargers),
            "price_per_kwh": cheapest["price"]["price"],
            "currency": cheapest["price"]["currency"],
            "street": cheapest["address"]["streetAddress"],
            "postal_code": cheapest["address"]["postalCode"],
            "city": cheapest["address"]["city"],
            "latitude": cheapest["coordinates"]["latitude"],
            "longitude": cheapest["coordinates"]["longitude"],
            "charger_id": cheapest["id"],
            "raw_data": cheapest,
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

        self._attr_name = "ANWB Charger Count"
        self._attr_unique_id = "anwb_charger_count"
        self._attr_icon = "mdi:ev-station"

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def native_value(self):

        return len(
            self.coordinator.data.get(
                "value",
                []
            )
        )
