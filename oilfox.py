import logging
from dateutil import parser
from datetime import datetime
from enum import Enum

from aiohttp import ClientSession
from requests import post

from homeassistant.const import MASS_KILOGRAMS, VOLUME_LITERS
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

class OilfoxError(Enum):
    NO_METERING = "NO_METERING"
    EMPTY_METERING = "EMPTY_METERING"
    NO_EXTRACTED_VALUE = "NO_EXTRACTED_VALUE"
    SENSOR_CONFIG = "SENSOR_CONFIG"
    MISSING_STORAGE_CONFIG = "MISSING_STORAGE_CONFIG"
    INVALID_STORAGE_CONFIG = "INVALID_STORAGE_CONFIG"
    DISTANCE_TOO_SHORT = "DISTANCE_TOO_SHORT"
    ABOVE_STORAGE_MAX = "ABOVE_STORAGE_MAX"
    BELOW_STORAGE_MIN = "BELOW_STORAGE_MIN"


def _convert_to_battery_percentage(battery: str) -> int:
    if battery == "FULL":
        return 100
    elif battery == "GOOD":
        return 70
    elif battery == "MEDIUM":
        return 50
    elif battery == "WARNING":
        return 20
    elif battery == "CRITICAL":
        return 10
    raise InvalidValue


def _convert_to_hass_unit(unit: str) -> str:
    if unit == "L":
        return VOLUME_LITERS
    elif unit == "kg":
        return MASS_KILOGRAMS
    raise InvalidValue


class OilfoxDevice:
    hwid: str
    currentMeteringAt: datetime
    nextMeteringAt: datetime
    daysReach: int
    error: OilfoxError | None
    batteryLevel: int
    fillLevelPercent: int
    fillLevelQuantity: int
    quantityUnit: str

    def __init__(
        self,
        hwid: str,
        currentMeteringAt: datetime,
        nextMeteringAt: datetime,
        error: OilfoxError | None,
        batteryLevel: int,
        fillLevelPercent: int,
        fillLevelQuantity: int,
        quantityUnit: str,
    ) -> None:
        self.hwid = hwid
        self.currentMeteringAt = currentMeteringAt
        self.nextMeteringAt = nextMeteringAt
        self.error = error
        self.batteryLevel = batteryLevel
        self.fillLevelPercent = fillLevelPercent
        self.fillLevelQuantity = fillLevelQuantity
        self.quantityUnit = quantityUnit


def create_oilfox_device_from_json(json: dict) -> OilfoxDevice:
    json_error = json.get("error", None)
    error = None if not json_error else OilfoxError(json_error)

    return OilfoxDevice(
        hwid=json["hwid"],
        currentMeteringAt=parser.parse(json["currentMeteringAt"]),
        nextMeteringAt=parser.parse(json["nextMeteringAt"]),
        error=error,
        batteryLevel=_convert_to_battery_percentage(json["batteryLevel"]),
        fillLevelPercent=json["fillLevelPercent"],
        fillLevelQuantity=json["fillLevelQuantity"],
        quantityUnit=_convert_to_hass_unit(json["quantityUnit"]),
    )


class OilfoxHub:
    session: ClientSession

    access_token: str
    refresh_token: str

    retries = 0

    def __init__(self, session: ClientSession) -> None:
        self.session = session

    async def authenticate(self, email: str, password: str) -> bool:
        credentials = {"password": password, "email": email}
        async with self.session.post(
            "https://api.oilfox.io/customer-api/v1/login", json=credentials
        ) as request:
            if request.status != 200:
                return False

            json_body = await request.json()

            self.access_token = json_body["access_token"]
            self.refresh_token = json_body["refresh_token"]
                

            return True

    async def refresh_authorization(self) -> bool:
        if self.retries > 2:
            raise FailedReauthError

        self.retries += 1

        _LOGGER.info(f"Refreshing tokens (Try {self.retries})")

        async with self.session.post(
            f"https://api.oilfox.io/customer-api/v1/token?refresh_token={self.refresh_token}") as request:
            if request.status != 200:
                return False

            json_body = await request.json()

            self.access_token = json_body["access_token"]
            self.refresh_token = json_body["refresh_token"]
            
            self.retries = 0

            return True

    async def list_devices(self) -> list[OilfoxDevice]:
        headers = {"authorization": f"Bearer {self.access_token}"}
        async with self.session.get(
            f"https://api.oilfox.io/customer-api/v1/device", headers=headers
        ) as request:
            if request.status == 401:
                await self.refresh_authorization()
                return await self.list_devices()

            json_body = await request.json()
            devices = [
                create_oilfox_device_from_json(entry)
                for entry in json_body["items"]
            ]
            return devices


class InvalidValue(HomeAssistantError):
    """Error to indicate that the value was unknown."""

class FailedReauthError(HomeAssistantError):
    """Error to indicate that reauthorizing using the refresh token failed."""
