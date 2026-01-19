"""Config flow for Mining Ops integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_CONCURRENCY,
    CONF_DEVICE_TYPE,
    CONF_MINERS,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SUBNET,
    CONF_TIMEOUT,
    DEVICE_TYPE_BITAXE,
    DEVICE_TYPE_NMMINER,
    BITAXE_DEFAULT_CONCURRENCY,
    BITAXE_DEFAULT_SCAN_INTERVAL,
    BITAXE_DEFAULT_SUBNET,
    BITAXE_DEFAULT_TIMEOUT,
    DOMAIN,
    NMMINER_DEFAULT_PORT,
)
from .discovery_bitaxe import discover_miners

_LOGGER = logging.getLogger(__name__)


class InvalidSubnet(HomeAssistantError):
    """Error to indicate subnet is invalid."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""


class DiscoveryFailed(HomeAssistantError):
    """Error to indicate discovery failed."""


class MiningOpsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mining Ops."""

    VERSION = 1
    
    def __init__(self) -> None:
        """Initialize."""
        super().__init__()
        self.discovered_miners: list[str] = []
        self.device_type: str | None = None
        self.config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - select device type."""
        if user_input is not None:
            self.device_type = user_input[CONF_DEVICE_TYPE]
            
            if self.device_type == DEVICE_TYPE_NMMINER:
                return await self.async_step_nmminer_config()
            elif self.device_type == DEVICE_TYPE_BITAXE:
                return await self.async_step_bitaxe_config()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_TYPE): vol.In(
                        {
                            DEVICE_TYPE_NMMINER: "NMMiner (UDP Broadcast)",
                            DEVICE_TYPE_BITAXE: "Bitaxe (HTTP API)",
                        }
                    ),
                }
            ),
            description_placeholders={},
        )

    async def async_step_nmminer_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure NMMiner settings."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            port = user_input[CONF_PORT]
            
            # Validate port
            if not 1 <= port <= 65535:
                errors[CONF_PORT] = "invalid_port"
            else:
                # Check if already configured
                await self.async_set_unique_id(f"nmminer_{port}")
                self._abort_if_unique_id_configured()
                
                # Store config and create entry
                config_data = {
                    CONF_DEVICE_TYPE: DEVICE_TYPE_NMMINER,
                    CONF_PORT: port,
                }
                
                return self.async_create_entry(
                    title=f"NMMiner (Port {port})",
                    data=config_data,
                )
        
        return self.async_show_form(
            step_id="nmminer_config",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PORT, default=NMMINER_DEFAULT_PORT): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "port": str(NMMINER_DEFAULT_PORT),
            },
        )

    async def async_step_bitaxe_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Bitaxe settings."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate subnet
            try:
                ipaddress.IPv4Network(user_input[CONF_SUBNET], strict=False)
            except ValueError:
                errors[CONF_SUBNET] = "invalid_subnet"
            
            # Validate concurrency
            if not 1 <= user_input[CONF_CONCURRENCY] <= 100:
                errors[CONF_CONCURRENCY] = "invalid_concurrency"
            
            # Validate timeout
            if not 0.5 <= user_input[CONF_TIMEOUT] <= 10:
                errors[CONF_TIMEOUT] = "invalid_timeout"
            
            # Validate scan interval
            if user_input[CONF_SCAN_INTERVAL] < 0:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            
            if not errors:
                # Store config for later steps
                self.config_data = user_input
                return await self.async_step_bitaxe_discovery()
        
        return self.async_show_form(
            step_id="bitaxe_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SUBNET, default=BITAXE_DEFAULT_SUBNET
                    ): str,
                    vol.Required(
                        CONF_CONCURRENCY, default=BITAXE_DEFAULT_CONCURRENCY
                    ): int,
                    vol.Required(
                        CONF_TIMEOUT, default=BITAXE_DEFAULT_TIMEOUT
                    ): vol.All(vol.Coerce(float)),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=BITAXE_DEFAULT_SCAN_INTERVAL
                    ): int,
                }
            ),
            errors={},
            description_placeholders={
                "subnet_example": BITAXE_DEFAULT_SUBNET,
            },
        )

    async def async_step_bitaxe_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Scan subnet for Bitaxe miners."""
        errors: dict[str, str] = {}
        
        if user_input is None:
            # Start discovery scan
            self.context["title_placeholders"] = {
                "subnet": self.config_data[CONF_SUBNET]
            }
            
            try:
                self.discovered_miners = await discover_miners(
                    subnet=self.config_data[CONF_SUBNET],
                    concurrency=self.config_data[CONF_CONCURRENCY],
                    timeout=self.config_data[CONF_TIMEOUT],
                )
                
                if not self.discovered_miners:
                    # No miners found
                    return await self.async_step_bitaxe_discovery_none()
                
                # Show list of discovered miners
                return await self.async_step_bitaxe_select_miners()
            
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Discovery failed: %s", err)
                errors["base"] = "discovery_failed"
                return self.async_show_form(
                    step_id="bitaxe_discovery",
                    errors=errors,
                )
        
        # User triggered discovery again
        return self.async_show_form(
            step_id="bitaxe_discovery",
            description_placeholders={
                "subnet": self.config_data[CONF_SUBNET],
            },
        )

    async def async_step_bitaxe_discovery_none(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle case where no miners were discovered."""
        if user_input is not None:
            if user_input.get("continue"):
                return await self.async_step_bitaxe_select_miners()
            return await self.async_step_user()
        
        return self.async_show_form(
            step_id="bitaxe_discovery_none",
            description_placeholders={
                "subnet": self.config_data[CONF_SUBNET],
            },
        )

    async def async_step_bitaxe_select_miners(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which miners to add."""
        if user_input is not None:
            selected_miners = user_input.get(CONF_MINERS, [])
            
            if not selected_miners:
                # Require at least one miner
                return self.async_show_form(
                    step_id="bitaxe_select_miners",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_MINERS): cv.multi_select(
                                {ip: ip for ip in self.discovered_miners}
                            ),
                        }
                    ),
                    errors={"base": "no_miners_selected"},
                    description_placeholders={
                        "subnet": self.config_data[CONF_SUBNET],
                        "count": str(len(self.discovered_miners)),
                    },
                )
            
            # Create entry with selected miners
            config_data = self.config_data.copy()
            config_data[CONF_DEVICE_TYPE] = DEVICE_TYPE_BITAXE
            config_data[CONF_MINERS] = selected_miners
            
            await self.async_set_unique_id(f"bitaxe_{len(selected_miners)}")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"Bitaxe ({len(selected_miners)} miner{'s' if len(selected_miners) != 1 else ''})",
                data=config_data,
            )
        
        # Show list of discovered miners
        return self.async_show_form(
            step_id="bitaxe_select_miners",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MINERS): cv.multi_select(
                        {ip: ip for ip in self.discovered_miners}
                    ),
                }
            ),
            description_placeholders={
                "subnet": self.config_data[CONF_SUBNET],
                "count": str(len(self.discovered_miners)),
            },
        )
