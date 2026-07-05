from homeassistant.components.sensor import (
    SensorEntity,
)

from .coordinator import (
    AnwbCoordinator,
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

    async_add_entities(
        [
            CheapestChargerSensor(
                coordinator
            )
        ]
    )


class CheapestChargerSensor(
    SensorEntity
):

    def __init__(
        self,
        coordinator,
    ):

        self.coordinator = coordinator

    @property
    def name(self):
        return "ANWB Cheapest Charger"

    @property
    def unique_id(self):
        return "anwb_cheapest"

    @property
    def state(self):

        chargers = (
            self.coordinator.data.get(
                "value",
                [],
            )
        )

        if not chargers:
            return None

        cheapest = min(
            chargers,
            key=lambda x: x["price"]["price"]
        )

        return cheapest["title"]

    @property
    def extra_state_attributes(self):

        chargers = (
            self.coordinator.data.get(
                "value",
                [],
            )
        )

        if not chargers:
            return {}

        cheapest = min(
            chargers,
            key=lambda x: x["price"]["price"]
        )

        return cheapest
