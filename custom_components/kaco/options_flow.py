from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class KacoInverterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Kaco options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional("name", default=self.config_entry.data.get("name", "")): str,
            vol.Optional("time", default=self.config_entry.data.get("time", 300)): int,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
