"""Sensor platform for Mining Ops integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_NMMINER,
    DEVICE_TYPE_BITAXE,
    DEVICE_TYPE_POOL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MiningOpsSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[dict[str, Any]], Any]


@dataclass
class MiningOpsSensorEntityDescription(
    SensorEntityDescription, MiningOpsSensorEntityDescriptionMixin
):
    """Describes Mining Ops sensor entity."""

    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def parse_hashrate(hashrate_str: str) -> float:
    """Parse hashrate string to numeric H/s."""
    try:
        hashrate_str = hashrate_str.replace("H/s", "").replace("h/s", "").strip()
        
        if "M" in hashrate_str or "m" in hashrate_str:
            return float(hashrate_str.replace("M", "").replace("m", "").strip()) * 1000000
        if "K" in hashrate_str or "k" in hashrate_str:
            return float(hashrate_str.replace("K", "").replace("k", "").strip()) * 1000
        return float(hashrate_str)
    except (ValueError, AttributeError):
        return 0.0


def get_share_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Get share statistics as attributes."""
    try:
        share = data.get("Share", "0/0")
        parts = share.split("/")
        if len(parts) >= 2:
            accepted_int = int(parts[0])
            total_int = int(parts[1])
            rejection_rate = (
                round((total_int - accepted_int) / total_int * 100, 2)
                if total_int > 0
                else 0
            )
            return {
                "accepted": accepted_int,
                "total": total_int,
                "rejection_rate": rejection_rate,
            }
    except (ValueError, AttributeError, IndexError):
        pass
    return {}


def get_difficulty_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Get difficulty statistics as attributes."""
    return {
        "pool_diff": data.get("PoolDiff", "0").strip(),
        "last_diff": data.get("LastDiff", "0").strip(),
        "net_diff": data.get("NetDiff", "0").strip(),
    }


def get_version_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Get version and board info as attributes."""
    return {
        "board_type": data.get("BoardType", "Unknown"),
        "free_heap": data.get("FreeHeap", 0),
    }


def _calculate_efficiency(data: dict[str, Any]) -> float:
    """Calculate J/GH from power and hashrate."""
    try:
        power = data.get("power", 0)
        hashrate = data.get("hashRate", 0)
        
        if hashrate > 0:
            hashrate_gh = hashrate / 1_000_000_000
            efficiency = power / hashrate_gh
            return round(efficiency, 2)
    except (ValueError, ZeroDivisionError):
        pass
    return 0


# ============================================================================
# NMMiner Sensor Types
# ============================================================================

NMMINER_SENSOR_TYPES: tuple[MiningOpsSensorEntityDescription, ...] = (
    MiningOpsSensorEntityDescription(
        key="hashrate",
        name="Hashrate",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
        value_fn=lambda data: parse_hashrate(data.get("HashRate", "0")),
    ),
    MiningOpsSensorEntityDescription(
        key="shares",
        name="Shares",
        icon="mdi:chart-line",
        value_fn=lambda data: data.get("Share", "0/0"),
        attr_fn=get_share_attributes,
    ),
    MiningOpsSensorEntityDescription(
        key="valid_blocks",
        name="Valid Blocks",
        icon="mdi:bitcoin",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("Valid", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="best_diff",
        name="Best Difficulty",
        icon="mdi:trophy",
        value_fn=lambda data: data.get("BestDiff", "0").strip(),
        attr_fn=get_difficulty_attributes,
    ),
    MiningOpsSensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("Temp", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        value_fn=lambda data: data.get("Uptime", "000d 00:00:00").split("\r")[0] if data.get("Uptime") else "000d 00:00:00",
    ),
    MiningOpsSensorEntityDescription(
        key="rssi",
        name="WiFi Signal",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("RSSI", -100),
    ),
    MiningOpsSensorEntityDescription(
        key="pool",
        name="Pool",
        icon="mdi:server-network",
        value_fn=lambda data: data.get("PoolInUse", "Unknown"),
    ),
    MiningOpsSensorEntityDescription(
        key="version",
        name="Firmware Version",
        icon="mdi:information-outline",
        value_fn=lambda data: data.get("Version", "Unknown"),
        attr_fn=get_version_attributes,
    ),
)

# ============================================================================
# Bitaxe Sensor Types (26 sensors - comprehensive monitoring)
# ============================================================================

BITAXE_SENSOR_TYPES: tuple[MiningOpsSensorEntityDescription, ...] = (
    # Device Info
    MiningOpsSensorEntityDescription(
        key="device_model",
        name="Device Model",
        icon="mdi:information",
        value_fn=lambda data: data.get("deviceModel", "Unknown"),
    ),
    MiningOpsSensorEntityDescription(
        key="connected",
        name="Connected",
        icon="mdi:lan-connect",
        value_fn=lambda data: "Yes" if data.get("stratum", {}).get("pools", [{}])[0].get("connected", False) else "No",
    ),
    
    # Mining Stats
    MiningOpsSensorEntityDescription(
        key="hashrate",
        name="Hashrate",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
        value_fn=lambda data: data.get("hashRate", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="shares_accepted",
        name="Shares Accepted",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:check-circle",
        value_fn=lambda data: data.get("sharesAccepted", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="shares_rejected",
        name="Shares Rejected",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:close-circle",
        value_fn=lambda data: data.get("sharesRejected", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="best_diff",
        name="Best Share Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:star",
        value_fn=lambda data: data.get("bestDiff", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="total_best_diff",
        name="Total Best Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:star-circle",
        value_fn=lambda data: data.get("stratum", {}).get("totalBestDiff", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_difficulty",
        name="Pool Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:target",
        value_fn=lambda data: data.get("poolDifficulty", 0),
    ),
    
    # Block Detection
    MiningOpsSensorEntityDescription(
        key="blocks_found",
        name="Blocks Found (This Pool)",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:diamond",
        value_fn=lambda data: data.get("foundBlocks", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="total_blocks_found",
        name="Total Blocks Found (All Time)",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:diamond-multiple",
        value_fn=lambda data: data.get("totalFoundBlocks", 0),
    ),
    
    # Temperature
    MiningOpsSensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("temp", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="vr_temperature",
        name="Voltage Regulator Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("vrTemp", 0),
    ),
    
    # Power
    MiningOpsSensorEntityDescription(
        key="power",
        name="Power Consumption",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("power", 0),
    ),
    
    # Voltage
    MiningOpsSensorEntityDescription(
        key="core_voltage",
        name="Core Voltage",
        native_unit_of_measurement="mV",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("coreVoltage", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="core_voltage_actual",
        name="Core Voltage Actual",
        native_unit_of_measurement="mV",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("coreVoltageActual", 0),
    ),
    
    # Cooling
    MiningOpsSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda data: data.get("fanspeed", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="fan_rpm",
        name="Fan RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda data: data.get("fanrpm", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="autofanspeed",
        name="Auto Fan Speed Mode",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan-auto",
        value_fn=lambda data: data.get("autofanspeed", 0),
    ),
    
    # System
    MiningOpsSensorEntityDescription(
        key="uptime",
        name="Uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-outline",
        value_fn=lambda data: data.get("uptimeSeconds", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="frequency",
        name="Core Frequency",
        native_unit_of_measurement="MHz",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("frequency", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="asic_count",
        name="ASIC Count",
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("asicCount", 0),
    ),
    
    # Efficiency
    MiningOpsSensorEntityDescription(
        key="efficiency",
        name="Efficiency",
        native_unit_of_measurement="J/GH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:leaf",
        value_fn=lambda data: _calculate_efficiency(data),
    ),
    
    # Network & Pool
    MiningOpsSensorEntityDescription(
        key="wifi_rssi",
        name="WiFi Signal Strength",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
        value_fn=lambda data: data.get("wifiRSSI", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="ssid",
        name="WiFi SSID",
        icon="mdi:wifi",
        value_fn=lambda data: data.get("ssid", "Unknown"),
    ),
    MiningOpsSensorEntityDescription(
        key="stratum_url",
        name="Stratum URL",
        icon="mdi:server",
        value_fn=lambda data: data.get("stratumURL", "Unknown"),
    ),
    MiningOpsSensorEntityDescription(
        key="stratum_port",
        name="Stratum Port",
        icon="mdi:server-network",
        value_fn=lambda data: data.get("stratumPort", 0),
    ),
)

# ============================================================================
# Pool Sensor Types (ckstats API - 25 sensors)
# ============================================================================

POOL_SENSOR_TYPES: tuple[MiningOpsSensorEntityDescription, ...] = (
    # Pool Status & Activity
    MiningOpsSensorEntityDescription(
        key="pool_id",
        name="Pool ID",
        icon="mdi:identifier",
        value_fn=lambda data: data.get("id", "Unknown"),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_runtime",
        name="Pool Runtime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-outline",
        value_fn=lambda data: data.get("runtime", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_timestamp",
        name="Pool Last Update",
        icon="mdi:clock-check-outline",
        value_fn=lambda data: data.get("timestamp", "Unknown"),
    ),
    
    # Pool Users & Workers
    MiningOpsSensorEntityDescription(
        key="pool_users",
        name="Connected Users",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:account-multiple",
        value_fn=lambda data: data.get("users", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_workers",
        name="Connected Workers",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lan-connect",
        value_fn=lambda data: data.get("workers", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_idle",
        name="Idle Workers",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sleep",
        value_fn=lambda data: data.get("idle", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_disconnected",
        name="Disconnected Workers",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lan-disconnect",
        value_fn=lambda data: data.get("disconnected", 0),
    ),
    
    # Hashrate Metrics (multiple timeframes)
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_1m",
        name="Pool Hashrate (1m)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate1m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_5m",
        name="Pool Hashrate (5m)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate5m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_15m",
        name="Pool Hashrate (15m)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate15m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_1h",
        name="Pool Hashrate (1h)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate1hr", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_6h",
        name="Pool Hashrate (6h)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate6hr", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_1d",
        name="Pool Hashrate (24h)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate1d", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_hashrate_7d",
        name="Pool Hashrate (7d)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate7d", 0),
    ),
    
    # Difficulty
    MiningOpsSensorEntityDescription(
        key="pool_difficulty",
        name="Network Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:target",
        value_fn=lambda data: data.get("diff", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_best_share",
        name="Best Share Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:star",
        value_fn=lambda data: data.get("bestshare", 0),
    ),
    
    # Shares
    MiningOpsSensorEntityDescription(
        key="pool_shares_accepted",
        name="Total Shares Accepted",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:check-circle",
        value_fn=lambda data: data.get("accepted", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_shares_rejected",
        name="Total Shares Rejected",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:close-circle",
        value_fn=lambda data: data.get("rejected", 0),
    ),
    
    # Shares Per Second
    MiningOpsSensorEntityDescription(
        key="pool_sps_1m",
        name="Shares Per Second (1m)",
        native_unit_of_measurement="SPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:share",
        value_fn=lambda data: data.get("SPS1m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_sps_5m",
        name="Shares Per Second (5m)",
        native_unit_of_measurement="SPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:share",
        value_fn=lambda data: data.get("SPS5m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_sps_15m",
        name="Shares Per Second (15m)",
        native_unit_of_measurement="SPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:share",
        value_fn=lambda data: data.get("SPS15m", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="pool_sps_1h",
        name="Shares Per Second (1h)",
        native_unit_of_measurement="SPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:share",
        value_fn=lambda data: data.get("SPS1h", 0),
    ),
)

# ============================================================================
# User Sensor Types (Primary/First User Stats - from /api/users)
# ============================================================================

USER_SENSOR_TYPES: tuple[MiningOpsSensorEntityDescription, ...] = (
    # User Identity
    MiningOpsSensorEntityDescription(
        key="user_address",
        name="User Address",
        icon="mdi:wallet",
        value_fn=lambda data: data.get("userAddress", "Unknown"),
    ),
    
    # User Hashrate
    MiningOpsSensorEntityDescription(
        key="user_hashrate_1h",
        name="User Hashrate (1h)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate1hr", 0),
    ),
    MiningOpsSensorEntityDescription(
        key="user_hashrate_1d",
        name="User Hashrate (24h)",
        native_unit_of_measurement="H/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("hashrate1d", 0),
    ),
    
    # User Shares
    MiningOpsSensorEntityDescription(
        key="user_shares",
        name="User Total Shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:share",
        value_fn=lambda data: data.get("shares", 0),
    ),
    
    # User Best Share
    MiningOpsSensorEntityDescription(
        key="user_best_share",
        name="User Best Share Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:star",
        value_fn=lambda data: data.get("bestEver", 0),
    ),
    
    # User Workers
    MiningOpsSensorEntityDescription(
        key="user_workers",
        name="User Worker Count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lan-connect",
        value_fn=lambda data: data.get("workerCount", 0),
    ),
    
    # User Last Share
    MiningOpsSensorEntityDescription(
        key="user_last_share",
        name="User Last Share Time",
        icon="mdi:clock-outline",
        value_fn=lambda data: _format_timestamp(data.get("lastShare", 0)),
    ),
)

# Helper function for timestamp formatting
def _format_timestamp(timestamp_ms: int | float) -> str:
    """Format millisecond timestamp to readable format."""
    if not timestamp_ms or timestamp_ms == 0:
        return "Never"
    try:
        from datetime import datetime
        timestamp_s = timestamp_ms / 1000
        dt = datetime.fromtimestamp(timestamp_s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return "Unknown"
    
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors based on device type."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    device_type = entry_data["device_type"]
    
    # Track which miners we've created entities for
    created_miners: set[str] = set()
    
    # Select sensor types based on device
    if device_type == DEVICE_TYPE_NMMINER:
        sensor_types = NMMINER_SENSOR_TYPES
    elif device_type == DEVICE_TYPE_BITAXE:
        sensor_types = BITAXE_SENSOR_TYPES
    elif device_type == DEVICE_TYPE_POOL:
        sensor_types = POOL_SENSOR_TYPES
    else:
        _LOGGER.error("Unknown device type: %s", device_type)
        return

    @callback
    def async_add_miner_sensors() -> None:
        """Add sensors for newly discovered miners."""
        new_entities: list[MiningOpsSensor] = []
        
        if device_type == DEVICE_TYPE_NMMINER:
            miners_dict = coordinator.miners
            miner_list = list(miners_dict.keys())
        elif device_type == DEVICE_TYPE_BITAXE:
            miner_list = list(coordinator.active_miners)
        else:
            return
        
        if not miner_list:
            return
        
        for miner_ip in miner_list:
            if miner_ip not in created_miners:
                _LOGGER.info("Creating sensors for %s miner %s", device_type, miner_ip)
                created_miners.add(miner_ip)
                
                for description in sensor_types:
                    new_entities.append(
                        MiningOpsSensor(
                            coordinator,
                            miner_ip,
                            description,
                            device_type,
                        )
                    )
        
        if new_entities:
            async_add_entities(new_entities)

    @callback
    def async_add_pool_sensors() -> None:
        """Add sensors for pool data."""
        new_entities: list[MiningOpsSensor] = []
        
        if "pool" not in created_miners:
            _LOGGER.info("Creating sensors for pool")
            created_miners.add("pool")
            
            for description in sensor_types:
                new_entities.append(
                    MiningOpsSensor(
                        coordinator,
                        "pool",
                        description,
                        device_type,
                    )
                )
        
        if new_entities:
            async_add_entities(new_entities)

    # Setup based on device type
    if device_type == DEVICE_TYPE_POOL:
        async_add_pool_sensors()
        coordinator.async_add_listener(async_add_pool_sensors)
    else:
        coordinator.async_add_listener(async_add_miner_sensors)
        async_add_miner_sensors()


class MiningOpsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mining Ops sensor."""

    entity_description: MiningOpsSensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        miner_ip: str,
        description: MiningOpsSensorEntityDescription,
        device_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._miner_ip = miner_ip
        self._device_type = device_type
        
        # Entity ID - replace dots with underscores
        safe_ip = miner_ip.replace(".", "_")
        self._attr_unique_id = f"{device_type}_{safe_ip}_{description.key}"
        
        # Device info
        if device_type == DEVICE_TYPE_NMMINER:
            device_name = f"NMMiner {miner_ip}"
            manufacturer = "NMTech"
            model = "NMMiner"
        elif device_type == DEVICE_TYPE_BITAXE:
            device_name = f"Bitaxe {miner_ip}"
            manufacturer = "Rigol"
            model = "BitAxe"
        elif device_type == DEVICE_TYPE_POOL:
            device_name = "Mining Pool (ckpool)"
            manufacturer = "ckpool"
            model = "ckpool (ckstats)"
        else:
            device_name = "Unknown"
            manufacturer = "Unknown"
            model = "Unknown"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, miner_ip)},
            "name": device_name,
            "manufacturer": manufacturer,
            "model": model,
        }
        
        # Entity name
        self._attr_name = f"{device_name} {description.name}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._device_type == DEVICE_TYPE_NMMINER:
            return self._miner_ip in self.coordinator.miners
        elif self._device_type == DEVICE_TYPE_BITAXE:
            if self._miner_ip not in self.coordinator.miners:
                return False
            data = self.coordinator.miners[self._miner_ip]
            return data.get("available", True)
        elif self._device_type == DEVICE_TYPE_POOL:
            return bool(self.coordinator.pool_data)
        
        return False

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._device_type == DEVICE_TYPE_NMMINER:
            if self._miner_ip not in self.coordinator.miners:
                return None
            data = self.coordinator.miners[self._miner_ip]
        elif self._device_type == DEVICE_TYPE_BITAXE:
            if self._miner_ip not in self.coordinator.miners:
                return None
            data = self.coordinator.miners[self._miner_ip]
            if not data.get("available", True):
                return None
        elif self._device_type == DEVICE_TYPE_POOL:
            data = self.coordinator.pool_data
            if not data:
                return None
        else:
            return None
        
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if self._device_type == DEVICE_TYPE_POOL:
            return None
        elif self._device_type == DEVICE_TYPE_NMMINER:
            if self._miner_ip not in self.coordinator.miners:
                return None
        else:
            if self._miner_ip not in self.coordinator.miners:
                return None
        
        if self.entity_description.attr_fn is None:
            return None
        
        data = self.coordinator.miners[self._miner_ip]
        return self.entity_description.attr_fn(data)