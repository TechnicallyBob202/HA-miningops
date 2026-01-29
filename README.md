# Mining Ops - Home Assistant Integration

A unified Home Assistant custom integration for monitoring Bitcoin mining operations. Supports both ESP32-based miners (NMMiner firmware) and Rigol Bitaxe miners.

## 🎯 Features

### Support for Multiple Device Types

#### NMMiner (UDP Broadcast)
- 🎛️ **UI Configuration** - Set up via Home Assistant UI (no YAML needed!)
- 🔄 **Real-time UDP Updates** - Push notifications every 5 seconds from miners
- 🎉 **Block Hit Events** - Get notified instantly when any miner finds a valid block
- 📊 **9+ Sensors** - Hashrate, shares, temperature, WiFi signal, uptime, and more
- ⚡ **Event-Driven** - Efficient push-based updates without network overhead

#### Bitaxe (HTTP API)
- 🔍 **Network Scanning** - Automatically discover Bitaxe miners on your subnet
- 🔄 **HTTP API Polling** - Regular updates from miner status endpoints
- 🔁 **Periodic Re-discovery** - Optionally scan for new miners on a schedule
- 📊 **25+ Sensors** - Hashrate, power, temperature, efficiency, uptime, ASIC count, and more
- 🎉 **Miner Events** - Get notified when miners are discovered or lost

### Common Features (Both Device Types)
- 🏗️ **Proper Architecture** - Uses DataUpdateCoordinator, config entries, and modern HA patterns
- 🔧 **Flexible Configuration** - Different setup flows for different mining hardware
- 📱 **Full Device Registry** - Each miner appears as a device with multiple sensors
- 🎨 **Custom Icon** - Branded icon for the integration
- 🌍 **Community Ready** - Well-documented, maintainable codebase

## 📦 Installation

### Manual Installation (Recommended)

1. **Create directory structure:**
   ```bash
   mkdir -p ~/.homeassistant/custom_components/miningops
   ```

2. **Copy integration files:**
   ```bash
   cp -r custom_components/miningops/* ~/.homeassistant/custom_components/miningops/
   ```

3. **Restart Home Assistant**
   - Settings → System → Restart

4. **Add Integration:**
   - Settings → Devices & Services
   - Click "+ Create Automation" → "+ Add Integration"
   - Search for "Mining Ops"
   - Select your device type and follow configuration

### File Structure

```
custom_components/miningops/
├── __init__.py                  # Entry point
├── const.py                     # Constants
├── config_flow.py               # Configuration flow
├── sensor.py                    # Sensor platform
├── strings.json                 # UI text localization
├── manifest.json                # Integration metadata
├── coordinator_nmminer.py       # NMMiner UDP coordinator
├── coordinator_bitaxe.py        # Bitaxe HTTP coordinator
└── discovery_bitaxe.py          # Bitaxe network discovery
```

## ⚙️ Configuration

### NMMiner (UDP-Based)

1. After adding the integration, select **"NMMiner (UDP Broadcast)"**
2. Configure the UDP port (default: 12345)
3. Click Submit
4. Your miners will auto-appear within seconds as they broadcast!

**What you need:**
- ESP32 miners running NMMiner firmware (v0.3.01+)
- Miners configured to broadcast on UDP port 12345
- Network connectivity between HA and miners

### Bitaxe (HTTP API)

1. After adding the integration, select **"Bitaxe (HTTP API)"**
2. Configure scanning options:
   - **Subnet**: Network range to scan (e.g., `192.168.1.0/24`)
   - **Concurrency**: Parallel probes (default: 20)
   - **Timeout**: Seconds per probe (default: 1.5)
   - **Scan Interval**: Re-scan frequency in seconds (0 = disabled)
3. Click Next to start discovery
4. Select which miners to monitor
5. Click Submit

**What you need:**
- Rigol Bitaxe miners on your network
- Bitaxe firmware with `/api/system/info` and `/api/system/metrics` endpoints
- Network connectivity between HA and miners

## 📊 Sensors

### NMMiner Sensors (Per Miner - 9 Total)

| Sensor | Description | Unit |
|--------|-------------|------|
| Hashrate | Current mining hashrate | H/s |
| Shares | Accepted/Total share ratio | - |
| Valid Blocks | Number of valid blocks found | - |
| Best Difficulty | Best difficulty achieved | - |
| Temperature | Device temperature | °C |
| Uptime | Miner uptime | Time format |
| WiFi Signal | RSSI signal strength | dBm |
| Pool | Current pool in use | - |
| Firmware Version | Miner firmware version | Version string |

### Bitaxe Sensors (Per Miner - 25 Total)

| Sensor | Description | Unit |
|--------|-------------|------|
| Device Model | Miner model name | - |
| Connected | Pool connection status | Yes/No |
| Hashrate | Current mining hashrate | H/s |
| Shares Accepted | Total accepted shares | - |
| Shares Rejected | Total rejected shares | - |
| Best Share Difficulty | Best share achieved | - |
| Total Best Difficulty | Total best difficulty | - |
| Pool Difficulty | Current pool difficulty | - |
| Blocks Found (This Pool) | Blocks found on current pool | - |
| Total Blocks Found | All-time blocks found | - |
| Temperature | Device temperature | °C |
| Voltage Regulator Temperature | VR temperature | °C |
| Power Consumption | Current power draw | W |
| Core Voltage | Core voltage setting | mV |
| Core Voltage Actual | Actual core voltage | mV |
| Fan Speed | Fan speed percentage | % |
| Fan RPM | Fan speed in RPM | RPM |
| Auto Fan Speed Mode | Auto cooling enabled | - |
| Uptime | Total device uptime | Seconds |
| Core Frequency | Operating frequency | MHz |
| ASIC Count | Number of ASIC chips | - |
| Efficiency | Power efficiency | J/GH |
| WiFi Signal Strength | WiFi RSSI signal | dBm |
| WiFi SSID | Connected WiFi network | - |
| Stratum URL | Mining pool URL | - |
| Stratum Port | Mining pool port | - |

## 🎉 Events

### nmminer_block_found
Fired when an NMMiner finds a valid block.

```python
{
    "device_type": "nmminer",
    "miner_ip": "192.168.1.101",
    "valid_blocks": 1,
    "best_diff": "4.021M",
    "hashrate": "113.13K"
}
```

### bitaxe_miner_discovered
Fired when a Bitaxe miner is discovered during periodic scanning.

```python
{
    "device_type": "bitaxe",
    "miner_ip": "192.168.1.105"
}
```

### bitaxe_miner_lost
Fired when a previously seen Bitaxe miner is no longer found.

```python
{
    "device_type": "bitaxe",
    "miner_ip": "192.168.1.105"
}
```

## 🤖 Automation Examples

### NMMiner Block Found Notification

```yaml
automation:
  - alias: "Mining Ops - Block Found"
    trigger:
      - platform: event
        event_type: nmminer_block_found
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💎 Bitcoin Block Found!"
          message: >
            Miner {{ trigger.event.data.miner_ip }} found a block!
            Valid Blocks: {{ trigger.event.data.valid_blocks }}
            Best Diff: {{ trigger.event.data.best_diff }}
```

### Bitaxe High Temperature Alert

```yaml
automation:
  - alias: "Mining Ops - High Temperature"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bitaxe_192_168_1_105_temperature
        above: 60
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ Miner Overheating"
          message: "Miner at {{ trigger.to_state.state }}°C"
```

### Miner Discovered Notification

```yaml
automation:
  - alias: "Mining Ops - New Miner Detected"
    trigger:
      - platform: event
        event_type: bitaxe_miner_discovered
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "✅ New Miner Detected"
          message: "Miner {{ trigger.event.data.miner_ip }} is now being monitored"
```

## 📈 Template Sensors

### Total Hashrate (Multi-Miner Fleet)

```yaml
template:
  - sensor:
      - name: "Total Mining Hashrate"
        unique_id: miningops_total_hashrate
        unit_of_measurement: "GH/s"
        state_class: measurement
        state: >
          {% set ns = namespace(total=0.0) %}
          {% for state in states.sensor 
             if 'miningops' in state.entity_id 
             and 'hashrate' in state.entity_id 
             and state.state not in ['unknown', 'unavailable'] %}
            {% set ns.total = ns.total + (state.state | float(0)) %}
          {% endfor %}
          {{ (ns.total / 1000000000) | round(3) }}
        icon: mdi:pickaxe
```

### Miner Health Monitor

```yaml
template:
  - binary_sensor:
      - name: "Mining Fleet Offline"
        unique_id: miningops_fleet_offline
        device_class: problem
        state: >
          {{ states.sensor 
             | selectattr('entity_id', 'search', 'miningops.*hashrate')
             | map(attribute='state')
             | select('eq', 'unavailable')
             | list | length > 0 }}
```

## 🔧 Troubleshooting

### NMMiner: No Miners Appearing

1. **Verify UDP broadcasts are reaching HA:**
   ```bash
   sudo tcpdump -i any -n udp port 12345 -A
   ```

2. **Check firewall:**
   ```bash
   sudo ufw allow 12345/udp
   ```

3. **Verify miners are broadcasting:**
   - Access miner's web interface
   - Confirm firmware version supports broadcasts

### Bitaxe: Discovery Not Finding Miners

1. **Verify subnet is correct:**
   - Check your network topology
   - Example: `ip addr show` on HA host

2. **Test miner connectivity:**
   ```bash
   curl http://192.168.1.105/api/system/info
   ```

3. **Check firewall:**
   ```bash
   sudo ufw allow http
   ```

### Sensors Show "Unavailable"

- Wait 30 seconds for first data fetch
- Check Home Assistant logs: Settings → System → Logs
- Ensure miners are online and accessible
- For NMMiner: verify UDP broadcasts aren't blocked
- For Bitaxe: verify API endpoints are responding

### Reinstalling

1. Settings → Integrations → Mining Ops → Delete
2. Delete `custom_components/miningops` folder
3. Restart Home Assistant
4. Re-add the integration

## 🏗️ Architecture

### NMMiner Data Flow
```
Miner (ESP32) → UDP Broadcast → NMMinerProtocol.datagram_received()
    ↓
NMMinerDataCoordinator.async_process_miner_data()
    ├─ Check for block hits
    ├─ Fire block_found event
    └─ Update sensor data
    ↓
Home Assistant sensors update
```

### Bitaxe Data Flow
```
Config Flow → Discovery Scan → Miner Selection
    ↓
BitaxeCoordinator
    ├─ Periodic HTTP polling (30s)
    ├─ Periodic network scan (optional)
    └─ Device registry management
    ↓
Home Assistant sensors update
```

## 📝 Development

### Adding New Sensors

#### For NMMiner
Edit `NMMINER_SENSOR_TYPES` in `sensor.py`:
```python
MiningOpsSensorEntityDescription(
    key="my_sensor",
    name="My Sensor",
    value_fn=lambda data: data.get("api_field", 0),
),
```

#### For Bitaxe
Edit `BITAXE_SENSOR_TYPES` in `sensor.py`:
```python
MiningOpsSensorEntityDescription(
    key="my_sensor",
    name="My Sensor",
    native_unit_of_measurement="unit",
    value_fn=lambda data: data.get("api_field", 0),
),
```

### Changing Discovery Logic

For Bitaxe network discovery, edit `discovery_bitaxe.py`:
- Modify `BITAXE_API_INFO_ENDPOINT` in `const.py`
- Adjust `_probe_ip()` verification logic
- Modify timeout or connection parameters

## 📚 References

- **NMMiner Firmware**: https://github.com/NMMiner1024/NMMiner
- **Bitaxe Hardware**: https://github.com/skot/bitaxe
- **Home Assistant Docs**: https://developers.home-assistant.io/
- **Home Assistant Community**: https://community.home-assistant.io/

## 📄 License

MIT License - See LICENSE file

## 🙋 Support

- Open an issue on GitHub
- Check existing issues/discussions first
- Include relevant logs from Settings → System → Logs
- Provide your HA version and integration version

## 🔄 Changelog

### v1.0.0 (2025-01-29)
- ✅ Split pool monitoring into separate integration
- ✅ Focused on miners only (NMMiner + Bitaxe)
- ✅ Removed all pool and user sensor types
- ✅ Cleaner configuration flow

---

**Happy Mining!** 🚀⛏️
