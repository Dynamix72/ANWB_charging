from math import radians
from math import sin
from math import cos
from math import sqrt
from math import atan2


EARTH_RADIUS_KM = 6371.0


def haversine(
    lat1,
    lon1,
    lat2,
    lon2,
):
    """
    Afstand tussen twee GPS punten in km.
    """

    dlat = radians(
        lat2 - lat1
    )

    dlon = radians(
        lon2 - lon1
    )

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return (
        EARTH_RADIUS_KM * c
    )


def route_index(
    lat,
    lon,
    route_points,
):
    """
    Zoek dichtstbijzijnde punt
    op de route.
    """

    best_index = 0

    best_distance = (
        float("inf")
    )

    for idx, point in enumerate(
        route_points
    ):

        point_lon = point[0]
        point_lat = point[1]

        distance = haversine(
            lat,
            lon,
            point_lat,
            point_lon,
        )

        if (
            distance
            < best_distance
        ):

            best_distance = (
                distance
            )

            best_index = idx

    return best_index


def distance_to_route(
    charger_lat,
    charger_lon,
    route_points,
):
    """
    Kortste afstand tussen
    laadpaal en route.
    """

    shortest = (
        float("inf")
    )

    for point in route_points:

        route_lon = point[0]
        route_lat = point[1]

        distance = haversine(
            charger_lat,
            charger_lon,
            route_lat,
            route_lon,
        )

        shortest = min(
            shortest,
            distance,
        )

    return shortest


def is_ahead_on_route(
    charger_lat,
    charger_lon,
    vehicle_lat,
    vehicle_lon,
    route_points,
):
    """
    Controleer of laadpaal
    voor of achter de auto ligt.
    """

    vehicle_idx = (
        route_index(
            vehicle_lat,
            vehicle_lon,
            route_points,
        )
    )

    charger_idx = (
        route_index(
            charger_lat,
            charger_lon,
            route_points,
        )
    )

    return (
        charger_idx
        > vehicle_idx
    )


def charger_power(
    charger,
):
    """
    Hoogste vermogen van
    alle connectoren.
    """

    highest_power = 0

    for evse in charger.get(
        "electricVehicleSupplyEquipment",
        [],
    ):

        for connector in evse.get(
            "connectors",
            [],
        ):

            highest_power = max(
                highest_power,
                connector.get(
                    "maxPowerInKW",
                    0,
                ),
            )

    return highest_power


def charger_is_available(
    charger,
):
    """
    Laadpaal heeft minimaal
    één connector beschikbaar.
    """

    evses = charger.get(
        "electricVehicleSupplyEquipment",
        [],
    )

    for evse in evses:

        status = (
            evse.get(
                "status"
            )
        )

        if status in (
            "AVAILABLE",
            "CHARGING",
        ):
            return True

    return False


def charger_price(
    charger,
):
    """
    Prijs uit ANWB response.
    """

    price = (
        charger
        .get("price", {})
        .get("price")
    )

    if price is None:
        return 999

    try:
        return float(price)
    except Exception:
        return 999


def classify_power(
    power_kw,
):
    """
    Type laadpaal.
    """

    if power_kw < 50:
        return "AC"

    if power_kw < 100:
        return "FAST"

    return "ULTRA"


def power_filter_match(
    power_kw,
    mode,
):
    """
    Filter op laadtype.
    """

    if mode == "Alle laders":
        return True

    if mode == "AC laders":
        return power_kw < 50

    if mode == "Snelladers":
        return (
            50
            <= power_kw
            < 100
        )

    if mode == "Ultrasnelladers":
        return (
            power_kw
            >= 100
        )

    return True


def filter_chargers_on_route(
    chargers,
    route_points,
    vehicle_lat,
    vehicle_lon,
    charger_mode,
    min_power_kw,
    max_route_distance_km,
):
    """
    Hoofdfilter voor
    routeplanning.
    """

    result = []

    for charger in chargers:

        if not charger_is_available(
            charger
        ):
            continue

        lat = charger[
            "coordinates"
        ]["latitude"]

        lon = charger[
            "coordinates"
        ]["longitude"]

        power = charger_power(
            charger
        )

        if (
            power
            < min_power_kw
        ):
            continue

        if not power_filter_match(
            power,
            charger_mode,
        ):
            continue

        route_distance = (
            distance_to_route(
                lat,
                lon,
                route_points,
            )
        )

        if (
            route_distance
            > max_route_distance_km
        ):
            continue

        if not is_ahead_on_route(
            lat,
            lon,
            vehicle_lat,
            vehicle_lon,
            route_points,
        ):
            continue

        result.append(
            {
                "charger": charger,
                "power": power,
                "price": charger_price(
                    charger
                ),
                "distance_to_route":
                    round(
                        route_distance,
                        1,
                    ),
                "type":
                    classify_power(
                        power
                    ),
            }
        )

    result.sort(
        key=lambda x: (
            x["price"],
            -x["power"],
        )
    )

    return result
