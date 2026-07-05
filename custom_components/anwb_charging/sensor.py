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
            CheapestChargerSensor(
                coordinator
            )
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
    def native_value(self):

        if not self.coordinator.data:
            return "Geen data"

        chargers = self.coordinator.data.get(
            "value",
            []
        )

        if len(chargers) == 0:
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

        if len(chargers) == 0:
            return {}

        cheapest = min(
            chargers,
            key=lambda c: float(
                c["price"]["price"]
            )
        )

        return {
            "charger_count": len(chargers),
            "price_per_kwh": cheapest["price"]["price"],
            "currency": cheapest["price"]["currency"],
            "latitude": cheapest["coordinates"]["latitude"],
            "longitude": cheapest["coordinates"]["longitude"],
            "street": cheapest["address"]["streetAddress"],
            "postal_code": cheapest["address"]["postalCode"],
            "city": cheapest["address"]["city"],
            "full_data": cheapest,
        }
