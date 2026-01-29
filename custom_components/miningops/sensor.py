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
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_NMMINER,
    DEVICE_TYPE_BITAXE,
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
# Bitaxe Sensor Types
# ============================================================================

BITAXE_SENSOR_TYPES: tuple[MiningOpsSensorEntityDescription, ...] = (
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
    MiningOpsSensorEntityDescription(
        key="power",
        name="Power Consumption",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("power", 0),
    ),
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
    MiningOpsSensorEntityDescription(
        key="uptime",
        name="Uptime",
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
    MiningOpsSensorEntityDescription(
        key="efficiency",
        name="Efficiency",
        native_unit_of_measurement="J/GH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:leaf",
        value_fn=lambda data: _calculate_efficiency(data),
    ),
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
        
        # Device info setup
        if device_type == DEVICE_TYPE_NMMINER:
            device_name = f"NMMiner {miner_ip}"
            manufacturer = "NMTech"
            model = "NMMiner"
            device_id = miner_ip
        elif device_type == DEVICE_TYPE_BITAXE:
            device_name = f"Bitaxe {miner_ip}"
            manufacturer = "Rigol"
            model = "BitAxe"
            device_id = miner_ip
        else:
            device_name = "Unknown"
            manufacturer = "Unknown"
            model = "Unknown"
            device_id = "unknown"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
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
        else:
            return None
        
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if self._device_type == DEVICE_TYPE_NMMINER:
            if self._miner_ip not in self.coordinator.miners:
                return None
        else:
            if self._miner_ip not in self.coordinator.miners:
                return None
        
        if self.entity_description.attr_fn is None:
            return None
        
        data = self.coordinator.miners[self._miner_ip]
        return self.entity_description.attr_fn(data)
