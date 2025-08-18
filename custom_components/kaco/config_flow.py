from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class KacoInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kaco."""

    VERSION = 1

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):
        from .options_flow import KacoInverterOptionsFlowHandler
        return KacoInverterOptionsFlowHandler(config_entry)

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of the integration."""
        errors = {}
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        
        if user_input is not None:
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
                            
                            # Update the existing config entry
                            self.hass.config_entries.async_update_entry(
                                config_entry,
                                data=user_input,
                                title=name
                            )
                            return self.async_abort(reason="reconfigure_successful")
            except Exception:
                errors["base"] = "cannot_connect"

        # Pre-fill form with existing data
        existing_data = config_entry.data
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
            step_id="reconfigure",
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

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
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
                            return self.async_create_entry(title=name, data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Optional("name", default=""): str,  # Optional Name
            vol.Required("serial_number"): str,      # Required Serial
            vol.Optional("model", default="Model not provided"): str,  # Optional Model
            vol.Optional("mac_address", default=""): str,    # Optional MAC
            vol.Required("ip_address"): str,         # Required IP
            vol.Required("port", default=8484): int, # Required Port
            vol.Required("time", default=300): int,  # Required Update Interval
        })

        return self.async_show_form(
            step_id="user",
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
