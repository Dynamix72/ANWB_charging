from homeassistant.components.sensor import SensorEntity

from .coordinator import AnwbCoordinator


async def async_setup_entry(
    hass,
    entry,
    async_add_entities,
):

    coordinator = AnwbCoordinator(
        hass,
        entry.data["api_key"],
        entry.data["device_tracker"],
        entry.data["radius"],
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [AnwbCheapestSensor(coordinator)],
        True
    )


class AnwbCheapestSensor(
    SensorEntity
):

    def __init__(self, coordinator):

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
            self.coordinator.data["value"]
        )

        cheapest = min(
            chargers,
            key=lambda x: x["price"]["price"]
        )

        return cheapest["title"]

    @property
    def extra_state_attributes(self):

        chargers = (
            self.coordinator.data["value"]
        )

        cheapest = min(
            chargers,
            key=lambda x: x["price"]["price"]
        )

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

            "latitude":
                cheapest["coordinates"]["latitude"],

            "longitude":
                cheapest["coordinates"]["longitude"],

            "availability":
                cheapest[
                    "electricVehicleSupplyEquipment"
                ],

            "raw":
                cheapest
        }
