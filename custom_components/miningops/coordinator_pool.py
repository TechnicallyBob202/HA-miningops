"""Pool coordinator for Mining Ops integration (ckstats)."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_POOL_HOST,
    CONF_POOL_PORT,
    DOMAIN,
    MANUFACTURER_CKPOOL,
    MODEL_CKPOOL,
    POOL_API_CURRENT_ENDPOINT,
    POOL_API_HEALTH_ENDPOINT,
    POOL_DEFAULT_POLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class PoolCoordinator(DataUpdateCoordinator):
    """Coordinator for Pool (ckstats) HTTP API polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POOL_DEFAULT_POLL_INTERVAL),
        )
        self.config = config
        self.host = config.get(CONF_POOL_HOST, "localhost")
        self.port = config.get(CONF_POOL_PORT, 5000)
        
        # Current pool data
        self.pool_data: dict[str, Any] = {}
        
        # Base URL for API
        self.base_url = f"http://{self.host}:{self.port}/api"

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data upon config entry setup."""
        # Check API health first
        health = await self._fetch_api(POOL_API_HEALTH_ENDPOINT)
        if not health:
            raise RuntimeError(
                f"Cannot connect to pool API at {self.base_url}. "
                f"Verify host ({self.host}) and port ({self.port}) are correct."
            )
        
        _LOGGER.info(
            "Pool API connection established: %s:%d",
            self.host,
            self.port,
        )
        
        # Register pool as device
        await self._register_pool_device()
        
        # Do initial data fetch
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Cleanup on shutdown."""
        pass

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current pool statistics."""
        try:
            # Get current pool stats
            current_stats = await self._fetch_api(POOL_API_CURRENT_ENDPOINT)
            
            if current_stats is None:
                _LOGGER.warning("Failed to fetch pool statistics")
                return self.pool_data or {}
            
            # Update stored data
            self.pool_data = current_stats
            
            _LOGGER.debug("Updated pool stats: %s", self.pool_data)
            return self.pool_data
        
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error fetching pool data: %s", err)
            return self.pool_data or {}

    async def _fetch_api(self, endpoint: str) -> dict[str, Any] | None:
        """Fetch JSON from pool API endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        _LOGGER.debug(
                            "API request to %s returned %d",
                            url,
                            response.status,
                        )
                        return None
        
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout fetching %s", url)
            return None
        except aiohttp.ClientError as err:
            _LOGGER.debug("Connection error to %s: %s", url, type(err).__name__)
            return None
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error fetching %s: %s", url, err)
            return None

    async def _register_pool_device(self) -> None:
        """Register pool as device in Home Assistant."""
        device_registry = async_get_device_registry(self.hass)
        
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry_id,
            identifiers={(DOMAIN, f"pool_{self.host}_{self.port}")},
            name="Mining Pool (ckpool)",
            manufacturer=MANUFACTURER_CKPOOL,
            model=MODEL_CKPOOL,
            hw_version=f"{self.host}:{self.port}",
        )
        _LOGGER.debug("Registered pool device")

    @property
    def config_entry_id(self) -> str | None:
        """Get config entry ID from coordinator."""
        return getattr(self, "_config_entry_id", None)