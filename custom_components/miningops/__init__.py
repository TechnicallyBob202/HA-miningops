"""The Mining Ops integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_NMMINER, DEVICE_TYPE_BITAXE, DOMAIN
from .coordinator_nmminer import NMMinerDataCoordinator
from .coordinator_bitaxe import BitaxeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mining Ops from a config entry."""
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_NMMINER)
    
    _LOGGER.info("Setting up Mining Ops integration for device type: %s", device_type)
    
    try:
        if device_type == DEVICE_TYPE_NMMINER:
            # Setup NMMiner (UDP-based)
            from .const import CONF_PORT, NMMINER_DEFAULT_PORT
            port = entry.data.get(CONF_PORT, NMMINER_DEFAULT_PORT)
            
            coordinator = NMMinerDataCoordinator(hass, port)
            await coordinator.async_start()
        
        elif device_type == DEVICE_TYPE_BITAXE:
            # Setup Bitaxe (HTTP API polling)
            coordinator = BitaxeCoordinator(hass, entry.data)
            coordinator._config_entry_id = entry.entry_id
            await coordinator.async_config_entry_first_refresh()
        
        else:
            _LOGGER.error("Unknown device type: %s", device_type)
            return False
    
    except OSError as err:
        _LOGGER.error("Failed to start Mining Ops listener: %s", err)
        return False
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Unexpected error during setup: %s", err)
        return False
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device_type": device_type,
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = entry_data["coordinator"]
        device_type = entry_data["device_type"]
        
        if device_type == DEVICE_TYPE_NMMINER:
            await coordinator.async_stop()
        elif device_type == DEVICE_TYPE_BITAXE:
            await coordinator.async_shutdown()
    
    return unload_ok
