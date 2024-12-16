"""Initialize the Kaco integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .options_flow import KacoInverterOptionsFlowHandler

DOMAIN = "kaco"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Kaco from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])

async def async_get_options_flow(config_entry):
    """Return the options flow for this entry."""
    return KacoInverterOptionsFlowHandler(config_entry)
