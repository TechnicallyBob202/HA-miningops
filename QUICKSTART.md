# Mining Ops - Quick Start Guide

## 🚀 30 Second Setup

### For NMMiner Users (ESP32 Miners)

1. **Add Integration:**
   - Settings → Devices & Services → "+ Create Automation" → "+ Add Integration"
   - Search "Mining Ops"
   - Select **"NMMiner (UDP Broadcast)"**

2. **Configure:**
   - UDP Port: `12345` (leave default unless changed)
   - Click Submit

3. **Done!**
   - Miners appear automatically as they broadcast
   - Typically within 5-10 seconds

### For Bitaxe Users (HTTP API Miners)

1. **Add Integration:**
   - Settings → Devices & Services → "+ Create Automation" → "+ Add Integration"
   - Search "Mining Ops"
   - Select **"Bitaxe (HTTP API)"**

2. **Configure Discovery:**
   - Subnet: `192.168.1.0/24` (adjust to your network)
   - Leave other settings at defaults
   - Click Next

3. **Select Miners:**
   - Check which miners to monitor
   - Click Submit

4. **Done!**
   - Sensors appear within 30 seconds

## 📊 What You Get

### Per NMMiner
- ⚡ Hashrate (realtime every 5 seconds)
- 🟦 Share statistics
- 💎 Valid blocks counter
- 🌡️ Temperature
- 📶 WiFi signal strength
- ⏱️ Uptime
- 🔗 Pool info
- 🎉 **Instant block notifications**

### Per Bitaxe
- ⚡ Hashrate
- 💡 Power consumption
- 🌡️ Temperature  
- 📊 Efficiency (J/GH)
- ⏱️ Uptime
- 🔧 ASIC count
- 🔔 Miner discovery/loss alerts

## 🎯 First Automation

### NMMiner: Block Found Alert

Go to Settings → Automations → Create automation

```yaml
alias: Mining Ops - Block Found
trigger:
  - platform: event
    event_type: nmminer_block_found
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "💎 Block Found!"
      message: "Miner {{ trigger.event.data.miner_ip }} - Block #{{ trigger.event.data.valid_blocks }}"
      data:
        priority: high
```

### Bitaxe: Temperature Alert

```yaml
alias: Mining Ops - Overheating
trigger:
  - platform: numeric_state
    entity_id: sensor.bitaxe_192_168_1_105_temperature
    above: 60
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "⚠️ Overheating"
      message: "Bitaxe temp: {{ trigger.to_state.state }}°C"
```

## 🔍 Finding Entity IDs

In Home Assistant:

1. Go to Developer Tools → States
2. Search for your miner IP (e.g., "192_168_1_101")
3. Click to see all sensors
4. Copy entity ID (e.g., `sensor.nmminer_192_168_1_101_hashrate`)

## ⚡ Pro Tips

### Combine Miners in Templates

Track total hashrate across ALL miners:

```yaml
template:
  - sensor:
      - name: "Total Hashrate"
        unique_id: total_hashrate
        unit_of_measurement: "GH/s"
        state: >
          {% set total = 0 %}
          {% for state in states.sensor 
             if 'miningops' in state.entity_id 
             and 'hashrate' in state.entity_id
             and state.state != 'unavailable' %}
            {% set total = total + (state.state | float(0)) %}
          {% endfor %}
          {{ (total / 1000000000) | round(3) }}
```

### Monitor Offline Miners

```yaml
template:
  - binary_sensor:
      - name: "Miners Offline"
        unique_id: miners_offline
        device_class: problem
        state: >
          {{ states.sensor 
             | selectattr('entity_id', 'search', 'miningops.*hashrate')
             | map(attribute='state')
             | select('eq', 'unavailable')
             | list | length > 0 }}
```

### Dashboard Widget

```yaml
type: glance
title: Mining Fleet
entities:
  - entity: sensor.nmminer_192_168_1_101_hashrate
    name: "Miner 1"
  - entity: sensor.nmminer_192_168_1_101_temperature
    name: "Temp 1"
  - entity: sensor.bitaxe_192_168_1_105_hashrate
    name: "Bitaxe 1"
  - entity: sensor.bitaxe_192_168_1_105_power
    name: "Power 1"
```

## 🆘 Quick Troubleshooting

### NMMiner: No miners showing up?

```bash
# Check if broadcasts are reaching HA (run on HA host)
sudo tcpdump -i any -n udp port 12345

# Allow port through firewall
sudo ufw allow 12345/udp

# Check miner is broadcasting
# Open miner web UI and verify version is v0.3.01+
```

### Bitaxe: Discovery finds nothing?

```bash
# Test if miner is reachable
ping 192.168.1.105

# Test if API is responding
curl http://192.168.1.105/api/system/info

# Check firewall
sudo ufw allow http
```

### Sensors say "unavailable"?

- **NMMiner**: Wait 30 seconds, check UDP broadcasts aren't blocked
- **Bitaxe**: Wait 30 seconds, verify `/api/system/info` returns JSON
- Both: Check Settings → System → Logs for error messages

## 📚 Next Steps

1. **Read Full Docs**: See README.md
2. **Create Automations**: Use examples above
3. **Build Dashboard**: Add visualizations
4. **Join Community**: Help others with similar setups

## 🎯 Common Setups

### Single NMMiner
```
Config: Default (port 12345)
Result: 1 device, 9 sensors
```

### Multiple Bitaxe Miners
```
Config: Subnet 192.168.1.0/24
Result: N devices, 6N sensors
Updates: Every 30 seconds
```

### Mixed Fleet (NMMiner + Bitaxe)
```
Config: Add 2 separate Mining Ops integrations
        - One for NMMiner (UDP)
        - One for Bitaxe (HTTP)
Result: Full fleet visibility in one place!
```

## ✨ Integration Highlights

| Feature | NMMiner | Bitaxe |
|---------|---------|--------|
| **Setup Speed** | ⚡ Instant auto-discover | ⏱️ Scan-based |
| **Update Rate** | ⚡ 5 seconds (push) | 🔄 30 seconds (pull) |
| **Block Alerts** | 🎉 Real-time events | - |
| **Network Overhead** | 💰 Minimal (push) | 📡 Light (pull) |
| **Setup Complexity** | 🟢 Simple | 🟡 Moderate |
| **Device Types** | ESP32 | Rigol Bitaxe |

---

**Ready to monitor your mining operation?** Let's get started! 🚀⛏️
