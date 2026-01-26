"""Constants for the Mining Ops integration."""
from typing import Final

DOMAIN: Final = "miningops"

# ============================================================================
# DEVICE TYPE CONFIGURATION
# ============================================================================

DEVICE_TYPE_NMMINER: Final = "nmminer"    # UDP-based ESP32 Bitcoin miners
DEVICE_TYPE_BITAXE: Final = "bitaxe"      # Rigol Bitaxe HTTP API miners
DEVICE_TYPE_POOL: Final = "pool"          # Mining pool (ckpool) statistics

# ============================================================================
# NMMiner UDP CONFIGURATION
# ============================================================================

NMMINER_DEFAULT_PORT: Final = 12345
NMMINER_UPDATE_INTERVAL: Final = 30  # Consider stale after 30s of no broadcasts

# ============================================================================
# Bitaxe HTTP CONFIGURATION
# ============================================================================

BITAXE_DEFAULT_SUBNET: Final = "192.168.1.0/24"
BITAXE_DEFAULT_CONCURRENCY: Final = 20
BITAXE_DEFAULT_TIMEOUT: Final = 1.5
BITAXE_DEFAULT_SCAN_INTERVAL: Final = 3600  # 1 hour
BITAXE_DEFAULT_POLL_INTERVAL: Final = 30    # 30 seconds

BITAXE_DISCOVERY_SIGNATURE: Final = "NerdQAxe"
BITAXE_API_INFO_ENDPOINT: Final = "/api/system/info"
BITAXE_API_STATS_ENDPOINT: Final = "/api/system/metrics"

# ============================================================================
# Pool (ckstats) HTTP CONFIGURATION
# ============================================================================

POOL_DEFAULT_HOST: Final = "localhost"
POOL_DEFAULT_PORT: Final = 5000
POOL_DEFAULT_POLL_INTERVAL: Final = 300  # 5 minutes for pool stats

POOL_API_CURRENT_ENDPOINT: Final = "/pool/current"
POOL_API_HISTORY_ENDPOINT: Final = "/pool/history"
POOL_API_UPTIME_ENDPOINT: Final = "/pool/uptime"
POOL_API_USERS_ENDPOINT: Final = "/users"
POOL_API_WORKERS_ENDPOINT: Final = "/workers"
POOL_API_HEALTH_ENDPOINT: Final = "/health"

# ============================================================================
# CONFIG FLOW KEYS
# ============================================================================

CONF_DEVICE_TYPE: Final = "device_type"

# NMMiner keys
CONF_PORT: Final = "port"

# Bitaxe keys
CONF_SUBNET: Final = "subnet"
CONF_CONCURRENCY: Final = "concurrency"
CONF_TIMEOUT: Final = "timeout"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_MINERS: Final = "miners"

# Pool keys
CONF_POOL_HOST: Final = "pool_host"
CONF_POOL_PORT: Final = "pool_port"

# ============================================================================
# PLATFORMS
# ============================================================================

PLATFORMS: Final = ["sensor"]

# ============================================================================
# EVENTS
# ============================================================================

EVENT_BLOCK_FOUND: Final = "miningops_block_found"
EVENT_MINER_DISCOVERED: Final = "miningops_miner_discovered"
EVENT_MINER_LOST: Final = "miningops_miner_lost"

# ============================================================================
# DEVICE INFO
# ============================================================================

MANUFACTURER_NMMINER: Final = "NMTech"
MODEL_NMMINER: Final = "NMMiner"

MANUFACTURER_BITAXE: Final = "Rigol"
MODEL_BITAXE: Final = "BitAxe"

MANUFACTURER_CKPOOL: Final = "ckpool"
MODEL_CKPOOL: Final = "ckpool (ckstats)"