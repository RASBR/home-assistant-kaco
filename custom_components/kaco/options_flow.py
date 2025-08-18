from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class KacoInverterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Kaco options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # Test connection with new settings
            serial_number = user_input.get("serial_number")
            name = user_input.get("name") or f"Kaco {serial_number}"
            ip_address = user_input.get("ip_address")
            port = user_input.get("port", 8484)
            update_interval = user_input.get("time", 300)

            url = f"http://{ip_address}:{port}/getdevdata.cgi?device=2&sn={serial_number}"
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            errors["base"] = "cannot_connect"
                        else:
                            user_input["url"] = url
                            user_input["name"] = name
                            user_input["time"] = update_interval
                            
                            # Update the config entry data, not just options
                            self.hass.config_entries.async_update_entry(
                                self.config_entry,
                                data=user_input,
                                title=name
                            )
                            return self.async_create_entry(title="", data={})
            except Exception:
                errors["base"] = "cannot_connect"

        # Pre-fill form with existing data from config entry
        existing_data = self.config_entry.data
        data_schema = vol.Schema({
            vol.Optional("name", default=existing_data.get("name", "")): str,
            vol.Required("serial_number", default=existing_data.get("serial_number", "")): str,
            vol.Optional("model", default=existing_data.get("model", "Model not provided")): str,
            vol.Optional("mac_address", default=existing_data.get("mac_address", "")): str,
            vol.Required("ip_address", default=existing_data.get("ip_address", "")): str,
            vol.Required("port", default=existing_data.get("port", 8484)): int,
            vol.Required("time", default=existing_data.get("time", 300)): int,
        })

        return self.async_show_form(
            step_id="init", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "name_hint": "If left empty will default to Kaco + Serial Number",
                "serial_hint": "Serial number should look like 3.7NX15620745",
                "model_hint": "Enter the inverter model (e.g., 3.7NX, 5.0NX, 8.8NX)",
                "mac_hint": "Optional. Used to match with network integration device",
                "ip_hint": "Example: 192.168.10.52 (Use a static IP)",
                "port_hint": "Default: 8484. Port of the device's API.",
                "time_hint": "Interval in seconds for polling the device"
            }
        )
