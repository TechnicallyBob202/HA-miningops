# Mining Ops - Installation Guide

## Prerequisites

- Home Assistant 2024.1.0 or newer
- Local network access to your mining devices
- SSH access to Home Assistant (for manual installation)

## Installation Methods

### Method 1: Manual Installation (Recommended for Custom Icons)

**Step 1: Connect to Home Assistant**

```bash
# Via SSH
ssh -i your_key.pem root@homeassistant.local
# Or: ssh username@homeassistant.local

# Navigate to config
cd ~/.homeassistant
```

**Step 2: Create Directory**

```bash
mkdir -p custom_components/miningops
cd custom_components/miningops
```

**Step 3: Copy Files**

Option A: Using Git
```bash
git clone https://github.com/TechnicallyBob202/HA-miningops.git
cp HA-miningops/custom_components/miningops/* ./
```

Option B: Using SCP (from your computer)
```bash
scp -r custom_components/miningops/* \
  user@homeassistant.local:~/.homeassistant/custom_components/miningops/
```

**Step 4: Verify Installation**

```bash
ls -la ~/.homeassistant/custom_components/miningops/

# Should show:
# __init__.py
# config_flow.py
# const.py
# coordinator_bitaxe.py
# coordinator_nmminer.py
# discovery_bitaxe.py
# manifest.json
# sensor.py
# strings.json
```

**Step 5: Restart Home Assistant**

- Settings → System → Restart Home Assistant
- Or via command: `systemctl restart homeassistant`

**Step 6: Add Integration**

- Settings → Devices & Services
- Click "+ Create Automation" → "+ Add Integration"
- Search for "Mining Ops"
- Follow the configuration wizard

### Method 2: Docker Installation

**If using Docker with volume mount:**

```bash
# In docker-compose.yml or docker run command:
volumes:
  - ./config:/config

# Copy integration
cp -r custom_components/miningops ./config/custom_components/

# Restart container
docker restart homeassistant
```

**Docker Compose Example:**

```yaml
version: '3'
services:
  homeassistant:
    container_name: homeassistant
    image: homeassistant/home-assistant:latest
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    network_mode: host  # Important for network scanning!
    restart: unless-stopped
```

### Method 3: Home Assistant OS (with Terminal Add-on)

**Step 1: Install Terminal & SSH Add-on**

1. Settings → Add-ons → Add-on Store
2. Search "Terminal & SSH"
3. Install and start

**Step 2: Connect via SSH**

```bash
ssh root@homeassistant.local
```

**Step 3: Download and Install**

```bash
cd /config
mkdir -p custom_components/miningops
cd custom_components/miningops

# Download files
# Option A: Clone repo
git clone https://github.com/TechnicallyBob202/HA-miningops.git
cp HA-miningops/custom_components/miningops/* ./

# Option B: Download via curl (if git not available)
curl -o __init__.py https://raw.githubusercontent.com/TechnicallyBob202/HA-miningops/main/custom_components/miningops/__init__.py
# ... repeat for all files
```

**Step 4: Restart**

- In Home Assistant: Settings → System → Restart

## Network Configuration

### For NMMiner (UDP)

**Allow UDP Port:**

```bash
# UFW firewall
sudo ufw allow 12345/udp

# firewalld
sudo firewall-cmd --add-port=12345/udp --permanent
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p udp --dport 12345 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

**Verify Broadcasts Reach HA:**

```bash
# From HA host - listen for broadcasts
sudo tcpdump -i any -n udp port 12345 -A -c 5

# Should see JSON payloads from miners every 5 seconds
```

### For Bitaxe (HTTP)

**Allow HTTP Access:**

```bash
# UFW
sudo ufw allow http

# firewalld
sudo firewall-cmd --add-service=http --permanent
sudo firewall-cmd --reload
```

**Verify Miner Accessibility:**

```bash
# From HA host - test API endpoint
curl http://192.168.1.105/api/system/info

# Should return JSON like:
# {"deviceModel":"bitaxe","hashRate":640000000,...}
```

### VLAN Separation

If miners are on different VLAN than HA:

```bash
# Verify routing is configured
ip route show

# Add static route if needed
sudo ip route add 192.168.10.0/24 via 192.168.1.1

# Make persistent (on Linux)
echo "192.168.10.0/24 via 192.168.1.1 dev eth0" | sudo tee -a /etc/network/interfaces
```

## Verification

### Check Files Are Installed

```bash
# Via SSH
ls -lah /config/custom_components/miningops/

# Should list all Python files and manifest.json
```

### Check Home Assistant Logs

```bash
# In Home Assistant:
Settings → System → Logs

# Or via SSH:
tail -f /config/home-assistant.log | grep -i mining
```

### Watch for Startup Message

```
[custom_components.miningops] Setting up Mining Ops integration for device type: nmminer
[custom_components.miningops] NMMiner UDP listener started on port 12345
```

### Verify Sensors Created

After adding integration:

1. Settings → Devices & Services
2. Look for "Mining Ops" entry
3. Click to expand
4. Should see devices and sensors

## Troubleshooting Installation

### Integration Not Showing in Add Integration

```bash
# 1. Check file permissions
chmod -R 755 /config/custom_components/miningops/

# 2. Clear Home Assistant cache
cd /config
rm -rf __pycache__ .homeassistant_cache

# 3. Restart Home Assistant
# Then clear browser cache (Ctrl+Shift+Delete)
```

### "No module named 'miningops'"

```bash
# Check file structure
tree /config/custom_components/miningops/

# Should show __init__.py in miningops directory
# Not: /custom_components/miningops/miningops/__init__.py
```

### Permission Errors

```bash
# Fix permissions (if running as specific user)
sudo chown -R homeassistant:homeassistant /config/custom_components/miningops/
sudo chmod -R 755 /config/custom_components/miningops/
```

### "Failed to load custom integration miningops"

Check logs:
```bash
# View recent errors
grep -i "error" /config/home-assistant.log | tail -20

# Look for syntax errors in Python files
python3 -m py_compile /config/custom_components/miningops/*.py
```

## File Locations by Setup Type

| Setup Type | Config Path | Integration Path |
|-----------|-------------|------------------|
| **Home Assistant OS** | `/config` | `/config/custom_components/miningops/` |
| **Home Assistant Supervised** | `/usr/share/hassio/homeassistant` | Same as above |
| **Docker** | `/config` (volume mount) | `/config/custom_components/miningops/` |
| **Manual Install** | `~/.homeassistant` | `~/.homeassistant/custom_components/miningops/` |

## Post-Installation

### Upgrade Integration

```bash
# Download latest version
cd /config/custom_components/miningops/
git pull  # or download new files

# Restart Home Assistant
# Settings → System → Restart
```

### Uninstall Integration

```bash
# Remove directory
rm -rf /config/custom_components/miningops/

# Remove from Home Assistant
# Settings → Integrations → Mining Ops → Delete

# Restart
# Settings → System → Restart
```

### Check Version

In Home Assistant:
- Settings → Devices & Services
- Find Mining Ops
- Click to expand
- Version shown at top

From command line:
```bash
grep '"version"' /config/custom_components/miningops/manifest.json
```

## Requirements

The integration has minimal dependencies:

- **aiohttp** - Already included in Home Assistant for HTTP requests
- **No additional pip packages needed**

## System Requirements

| Component | Minimum |
|-----------|---------|
| **Memory** | 50 MB for integration |
| **CPU** | Minimal (async operations) |
| **Disk** | 2 MB for integration files |
| **Network** | Local access to miners |
| **Python** | 3.11+ (included with HA) |

## Getting Help

1. **Check logs**: Settings → System → Logs
2. **Review README**: See README.md in integration
3. **Check QUICKSTART**: See QUICKSTART.md for common issues
4. **Verify network**: Ensure miners are accessible
5. **Open GitHub issue**: Include logs and configuration

## Common Issues

### "Integration not loading"
→ Check file permissions and Python syntax

### "Integration loads but no miners"
→ Check network connectivity to miners

### "Sensors unavailable"
→ Wait 30+ seconds, check API accessibility

### "High CPU during discovery"
→ Reduce Bitaxe concurrency setting (default: 20, try 5-10)

---

**Installation complete!** Proceed to [QUICKSTART.md](QUICKSTART.md) to begin monitoring your mining operation. 🚀
