"""Bitaxe network discovery for Mining Ops integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import aiohttp

from .const import BITAXE_API_INFO_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class BitaxeDiscovery:
    """Scan subnet for Bitaxe miners."""

    def __init__(
        self,
        subnet: str,
        concurrency: int = 20,
        timeout: float = 1.5,
    ) -> None:
        """Initialize discovery."""
        self.subnet = subnet
        self.concurrency = concurrency
        self.timeout = timeout
        self.sem = asyncio.Semaphore(concurrency)

    async def discover(self) -> list[str]:
        """Scan subnet for Bitaxe miners."""
        _LOGGER.info(
            "Starting Bitaxe discovery scan: subnet=%s, concurrency=%s, timeout=%s",
            self.subnet,
            self.concurrency,
            self.timeout,
        )
        
        try:
            network = ipaddress.IPv4Network(self.subnet, strict=False)
        except ValueError as err:
            _LOGGER.error("Invalid subnet format: %s", err)
            return []
        
        # Create probe task for each IP
        tasks = [self._probe_ip(str(ip)) for ip in network.hosts()]
        
        # Gather all results (ignore exceptions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None values and exceptions
        found_miners = [ip for ip in results if isinstance(ip, str)]
        
        _LOGGER.info("Bitaxe discovery complete: found %d miner(s)", len(found_miners))
        return found_miners

    async def _probe_ip(self, ip: str) -> str | None:
        """Probe single IP for Bitaxe miner."""
        async with self.sem:
            try:
                url = f"http://{ip}{BITAXE_API_INFO_ENDPOINT}"
                
                timeout = aiohttp.ClientTimeout(
                    total=self.timeout,
                    connect=self.timeout / 2,
                )
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check for expected Bitaxe API fields
                            if "deviceModel" in data and "hashRate" in data:
                                _LOGGER.debug(
                                    "Found Bitaxe miner at %s: %s",
                                    ip,
                                    data.get("deviceModel"),
                                )
                                return ip
                        
            except asyncio.TimeoutError:
                pass
            except aiohttp.ClientError as err:
                _LOGGER.debug("Connection error to %s: %s", ip, type(err).__name__)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.debug("Unexpected error probing %s: %s", ip, err)
            
            return None


async def discover_miners(
    subnet: str,
    concurrency: int = 20,
    timeout: float = 1.5,
) -> list[str]:
    """Convenience function for Bitaxe discovery."""
    discovery = BitaxeDiscovery(subnet, concurrency, timeout)
    return await discovery.discover()
