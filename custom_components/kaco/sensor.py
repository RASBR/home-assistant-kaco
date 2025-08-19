import aiohttp
import json
import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    {"key": "eto", "name": "Energy Total", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "factor": 0.1},
    {"key": "etd", "name": "Energy Today", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "factor": 0.1},
    {"key": "hto", "name": "Today Run Time", "unit": "h", "device_class": "duration", "state_class": "total_increasing", "factor": 1},
    {"key": "pac", "name": "Total Power", "unit": "W", "device_class": "power", "state_class": "measurement", "factor": 1},
    {"key": "pf", "name": "Power Factor", "unit": "%", "device_class": "power_factor", "state_class": "measurement", "factor": 1},

    {"key": "vac[0]", "name": "AC Voltage Output", "unit": "V", "device_class": "voltage", "state_class": "measurement", "factor": 0.1},
    {"key": "iac[0]", "name": "AC Current Output", "unit": "A", "device_class": "current", "state_class": "measurement", "factor": 0.1},
    {"key": "vpv[0]", "name": "DC Voltage Input 1", "unit": "V", "device_class": "voltage", "state_class": "measurement", "factor": 0.1},
    {"key": "vpv[1]", "name": "DC Voltage Input 2", "unit": "V", "device_class": "voltage", "state_class": "measurement", "factor": 0.1},
    {"key": "ipv[0]", "name": "DC Current Input 1", "unit": "A", "device_class": "current", "state_class": "measurement", "factor": 0.01},
    {"key": "ipv[1]", "name": "DC Current Input 2", "unit": "A", "device_class": "current", "state_class": "measurement", "factor": 0.01},

    # Statistical sensors for long-term statistics and energy dashboard compatibility
    {"key": "pac_stat", "name": "Power (stat)", "unit": "W", "device_class": "power", "state_class": "measurement", "factor": 1, "source_key": "pac", "entity_category": "diagnostic"},
    {"key": "etd_stat", "name": "Energy Today (stat)", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "factor": 0.1, "source_key": "etd", "entity_category": "diagnostic"},

    # Connection status sensor
    {"key": "connection_status", "name": "Connection Status", "unit": None, "device_class": None, "state_class": None, "factor": 1, "entity_category": "diagnostic"},

    # IP Address entity moved to Diagnostics by setting entity_category.
    {"key": "ip_address", "name": "IP Address", "unit": None, "device_class": None, "state_class": None, "factor": 1, "default_disabled": False},
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    url = entry.data["url"]
    update_interval = entry.options.get("time", entry.data.get("time", 300))
    mac_address = entry.data.get("mac_address", "")
    serial_number = entry.data.get("serial_number", "Unknown")
    model = entry.data.get("model", "Model not provided")
    device_name = entry.data.get("name", f"Kaco {serial_number}")

    coordinator = KacoInverterCoordinator(hass, url, update_interval, mac_address, device_name)
    await coordinator.async_request_refresh()

    entities = []
    for sensor in SENSORS:
        entities.append(KacoSensor(
            coordinator=coordinator,
            device_name=device_name,
            sensor=sensor,
            serial_number=serial_number,
            model=model,
            update_interval=update_interval
        ))

    async_add_entities(entities)


class KacoInverterCoordinator(DataUpdateCoordinator):
    """Class to fetch data and log unreachable/reachable states."""

    def __init__(self, hass, url, update_interval, mac_address, device_name):
        self.url = url
        self.mac_address = mac_address
        self.device_name = device_name
        self._was_unreachable = True
        super().__init__(
            hass,
            _LOGGER,
            name="Kaco",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url) as response:
                    raw_data = await response.text()
                    data = json.loads(raw_data)
                    if self._was_unreachable:
                        _LOGGER.info("%s is now reachable again.", self.device_name)
                    self._was_unreachable = False
                    return data
            except Exception as err:
                if not self._was_unreachable:
                    _LOGGER.warning("%s became unreachable.", self.device_name)
                self._was_unreachable = True
                raise UpdateFailed(f"Failed to fetch data: {err}") from err


class KacoSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Kaco Inverter sensor."""

    def __init__(self, coordinator, device_name, sensor, serial_number, model, update_interval):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._name = f"{device_name} {sensor['name']}"
        self._key = sensor["key"]
        self._unit = sensor["unit"]
        self._device_class = sensor["device_class"]
        self._state_class = sensor.get("state_class")
        self._factor = sensor.get("factor", 1)
        self._source_key = sensor.get("source_key")  # For statistical sensors that reference other sensor data
        self._attr_unique_id = f"{DOMAIN}_{device_name}_{sensor['key']}"
        self._serial_number = serial_number
        self._model = model
        self._update_interval = update_interval
        
        # Store last known state for persistence
        self._last_known_state = None

        # Set modern Home Assistant attributes
        if self._unit is not None:
            self._attr_unit_of_measurement = self._unit
        if self._device_class is not None:
            self._attr_device_class = self._device_class
        if self._state_class is not None:
            self._attr_state_class = self._state_class

        # Device info: Use dynamic model and include serial number
        device_info = {
            "identifiers": {(DOMAIN, device_name)},
            "manufacturer": "KACO new energy GmbH",
            "model": self._model,
            "name": device_name,
            "serial_number": self._serial_number
        }

        if self.coordinator.mac_address:
            device_info["connections"] = {("mac", self.coordinator.mac_address)}

        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = not sensor.get("default_disabled", False)

        # Set entity_category for organization on device page
        entity_category = sensor.get("entity_category")
        if entity_category == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif self._key == "ip_address":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        """Return True if entity is available."""
        # Connection status sensor shows actual availability
        if self._key == "connection_status":
            return True  # Always available to show online/offline status
        # All other sensors remain available with last known values
        return True

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._key == "connection_status":
            return "Online" if self.coordinator.last_update_success else "Offline"
            
        if self._key == "ip_address":
            return self.coordinator.url.split("//")[1].split(":")[0]

        # Handle statistical sensors that reference other sensor data
        if self._source_key:
            raw_value = self._get_nested_value(self._source_key, self.coordinator.data)
        else:
            raw_value = self._get_nested_value(self._key, self.coordinator.data)
            
        if raw_value is not None:
            try:
                current_state = round(float(raw_value) * self._factor, 2)
                self._last_known_state = current_state  # Store as last known
                return current_state
            except (ValueError, TypeError):
                return self._last_known_state  # Return last known on error
        
        # Return last known state if no current data available
        return self._last_known_state

    @property
    def extra_state_attributes(self):
        if self._key == "ip_address":
            return {
                "Manufacturer": "KACO new energy GmbH",
                "Model": "3.7NX",
                "Serial Number": self._serial_number,
                "Update Interval": self._update_interval,
                "Current Version": "1.0.0",
                "Latest Version": "1.0.0"
            }
        return None

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

    @property
    def state_class(self):
        return self._state_class

    def _get_nested_value(self, key, data):
        if "[" not in key:
            return data.get(key)

        parts = []
        buf = ""
        for char in key:
            if char == "[":
                parts.append(buf)
                buf = ""
            elif char == "]":
                if buf.isdigit():
                    parts.append(int(buf))
                buf = ""
            else:
                buf += char
        if buf:
            parts.append(buf)

        val = data
        for p in parts:
            if isinstance(p, int):
                if isinstance(val, list) and 0 <= p < len(val):
                    val = val[p]
                else:
                    return None
            else:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    return None
        return val
