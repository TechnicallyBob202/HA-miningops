"""Bitaxe coordinator for Mining Ops integration."""
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
    BITAXE_API_INFO_ENDPOINT,
    BITAXE_API_STATS_ENDPOINT,
    CONF_CONCURRENCY,
    CONF_MINERS,
    CONF_SCAN_INTERVAL,
    CONF_SUBNET,
    CONF_TIMEOUT,
    DOMAIN,
    EVENT_MINER_DISCOVERED,
    EVENT_MINER_LOST,
    MANUFACTURER_BITAXE,
    MODEL_BITAXE,
    BITAXE_DEFAULT_POLL_INTERVAL,
)
from .discovery_bitaxe import discover_miners

_LOGGER = logging.getLogger(__name__)


class BitaxeCoordinator(DataUpdateCoordinator):
    """Coordinator for Bitaxe HTTP API polling."""

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
            update_interval=timedelta(seconds=BITAXE_DEFAULT_POLL_INTERVAL),
        )
        self.config = config
        
        # Known miners from config
        self.configured_miners: set[str] = set(config.get(CONF_MINERS, []))
        
        # Currently active miners
        self.active_miners: set[str] = set(self.configured_miners)
        
        # Miner data: {ip: {stats}}
        self.miners: dict[str, dict[str, Any]] = {}
        
        # Periodic scan task
        self._scan_task: asyncio.Task | None = None
        
        # Discovery settings
        self.subnet = config.get(CONF_SUBNET)
        self.concurrency = config.get(CONF_CONCURRENCY, 20)
        self.timeout = config.get(CONF_TIMEOUT, 1.5)
        self.scan_interval = config.get(CONF_SCAN_INTERVAL, 3600)

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data upon config entry setup."""
        # Start periodic scan if configured
        if self.scan_interval > 0:
            self._scan_task = asyncio.create_task(self._periodic_scan())
        
        # Register devices in device registry
        await self._register_devices()
        
        # Do initial data fetch
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from all active miners."""
        tasks = [
            self._fetch_miner_data(ip)
            for ip in self.active_miners
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update miners dict
        for ip, data in zip(self.active_miners, results):
            if isinstance(data, dict):
                self.miners[ip] = data
            else:
                # Error fetching data, mark as unavailable but keep entry
                self.miners[ip] = {"available": False, "error": str(data)}
        
        return self.miners

    async def _fetch_miner_data(self, ip: str) -> dict[str, Any] | None:
        """Fetch data from single miner."""
        try:
            # Get system info
            info = await self._fetch_api(ip, BITAXE_API_INFO_ENDPOINT)
            
            # Get stats/metrics
            stats = await self._fetch_api(ip, BITAXE_API_STATS_ENDPOINT)
            
            if info is None:
                return None
            
            # Combine data
            data = {
                "available": True,
                "ip": ip,
                **info,
            }
            
            if stats:
                data["stats"] = stats
            
            _LOGGER.debug("Updated miner %s: %s", ip, data)
            return data
        
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Error fetching data from %s: %s", ip, err)
            return None

    async def _fetch_api(
        self,
        ip: str,
        endpoint: str,
    ) -> dict[str, Any] | None:
        """Fetch JSON from miner API endpoint."""
        url = f"http://{ip}{endpoint}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
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

    async def _periodic_scan(self) -> None:
        """Periodically scan subnet for new miners."""
        _LOGGER.info(
            "Starting periodic scan task (interval: %d seconds)",
            self.scan_interval,
        )
        
        while True:
            try:
                await asyncio.sleep(self.scan_interval)
                
                _LOGGER.debug("Running periodic discovery scan")
                found_miners = await discover_miners(
                    subnet=self.subnet,
                    concurrency=self.concurrency,
                    timeout=self.timeout,
                )
                
                found_set = set(found_miners)
                
                # Check for new miners
                new_miners = found_set - self.active_miners
                if new_miners:
                    _LOGGER.info("Found new miners: %s", new_miners)
                    for ip in new_miners:
                        self.hass.bus.async_fire(
                            EVENT_MINER_DISCOVERED,
                            {"device_type": "bitaxe", "miner_ip": ip},
                        )
                        self.active_miners.add(ip)
                
                # Check for lost miners
                lost_miners = self.active_miners - found_set - self.configured_miners
                if lost_miners:
                    _LOGGER.info("Lost miners: %s", lost_miners)
                    for ip in lost_miners:
                        self.hass.bus.async_fire(
                            EVENT_MINER_LOST,
                            {"device_type": "bitaxe", "miner_ip": ip},
                        )
                        self.active_miners.discard(ip)
            
            except asyncio.CancelledError:
                _LOGGER.debug("Periodic scan task cancelled")
                break
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error in periodic scan: %s", err)

    async def _register_devices(self) -> None:
        """Register miners as devices in Home Assistant."""
        device_registry = async_get_device_registry(self.hass)
        
        for ip in self.configured_miners:
            device_registry.async_get_or_create(
                config_entry_id=self.config_entry_id,
                identifiers={(DOMAIN, ip)},
                name=f"Bitaxe {ip}",
                manufacturer=MANUFACTURER_BITAXE,
                model=MODEL_BITAXE,
            )
            _LOGGER.debug("Registered device for miner %s", ip)

    @property
    def config_entry_id(self) -> str | None:
        """Get config entry ID from coordinator."""
        return getattr(self, "_config_entry_id", None)
