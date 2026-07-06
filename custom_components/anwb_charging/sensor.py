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
            ChargerListSensor(coordinator),
        ]
    )


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

        chargers = filter_valid_chargers(
            self.coordinator.data.get(
                "value",
                []
            )
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

        chargers = filter_valid_chargers(
            self.coordinator.data.get(
                "value",
                []
            )
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
            "charger_count": len(chargers),
            "price_per_kwh": cheapest["price"]["price"],
            "currency": cheapest["price"]["currency"],
            "street": cheapest["address"]["streetAddress"],
            "postal_code": cheapest["address"]["postalCode"],
            "city": cheapest["address"]["city"],
            "full_address":
                f"{cheapest['address']['streetAddress']}, "
                f"{cheapest['address']['postalCode']} "
                f"{cheapest['address']['city']}",
            "latitude": cheapest["coordinates"]["latitude"],
            "longitude": cheapest["coordinates"]["longitude"],
            "charger_id": cheapest["id"],
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

        chargers = filter_valid_chargers(
            self.coordinator.data.get(
                "value",
                []
            )
        )

        return len(chargers)


class ChargerListSensor(
    CoordinatorEntity,
    SensorEntity,
):

    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "ANWB Charger List"
        self._attr_unique_id = "anwb_charger_list"
        self._attr_icon = "mdi:format-list-bulleted"

    @property
    def native_value(self):

        chargers = filter_valid_chargers(
            self.coordinator.data.get(
                "value",
                []
            )
        )

        chargers = sorted(
            chargers,
            key=lambda c: float(
                c["price"]["price"]
            )
        )[:10]

        return len(chargers)

    @property
    def extra_state_attributes(self):

        chargers = filter_valid_chargers(
            self.coordinator.data.get(
                "value",
                []
            )
        )

        chargers = sorted(
            chargers,
            key=lambda c: float(
                c["price"]["price"]
            )
        )[:10]

        result = []

        for rank, charger in enumerate(
            chargers,
            start=1,
        ):

            status = "AVAILABLE"

            for evse in charger.get(
                "electricVehicleSupplyEquipment",
                []
            ):

                if evse.get("status") == "CHARGING":
                    status = "CHARGING"
                    break

            result.append(
                {
                    "rank": rank,
                    "name": charger["title"],
                    "address": charger["address"]["streetAddress"],
                    "postal_code": charger["address"]["postalCode"],
                    "city": charger["address"]["city"],
                    "full_address":
                        f"{charger['address']['streetAddress']}, "
                        f"{charger['address']['postalCode']} "
                        f"{charger['address']['city']}",
                    "price_per_kwh":
                        charger["price"]["price"],
                    "currency":
                        charger["price"]["currency"],
                    "status":
                        status,
                    "icon":
                        "mdi:lightning-bolt"
                        if status == "CHARGING"
                        else "mdi:ev-station",
                    "latitude":
                        charger["coordinates"]["latitude"],
                    "longitude":
                        charger["coordinates"]["longitude"],
                }
            )

        return {
            "chargers": result
        }
