<p align="center">
  <img src="img/logo.png" alt="LocalTuya 2.0" width="500">
</p>

<p align="center">
  <strong>LocalTuya 2.0 — The Next Generation of Local Tuya Control</strong><br>
  <sub>Maintained by <a href="https://bildassystem.cz">BildaSystem.cz</a></sub>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/Bildass/localtuya/releases"><img src="https://img.shields.io/github/v/release/Bildass/localtuya?style=for-the-badge&color=green" alt="Release"></a>
  <a href="https://github.com/Bildass/localtuya/stargazers"><img src="https://img.shields.io/github/stars/Bildass/localtuya?style=for-the-badge" alt="Stars"></a>
  <a href="https://github.com/Bildass/localtuya/blob/master/LICENSE"><img src="https://img.shields.io/github/license/Bildass/localtuya?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="#-why-this-fork">Why This Fork?</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-features">Features</a> •
  <a href="#-migration-guide">Migration</a> •
  <a href="#-documentation">Documentation</a>
</p>

<p align="center">
  🇬🇧 <strong>English</strong> | <a href="README.cs.md">🇨🇿 Čeština</a>
</p>

---

## 🤔 Why This Fork?

The original [LocalTuya](https://github.com/rospogrigio/localtuya) is a fantastic integration, but development has slowed down. **LocalTuya 2.0** picks up where it left off:

| Pain Point | Original LocalTuya | LocalTuya 2.0 Solution |
|------------|-------------------|---------------------|
| 😤 **Changing device IP/key** | Click through ALL entities one by one | ✅ **Quick Edit** - single window, done in seconds |
| 😤 **Editing one entity** | Must navigate through entire device | ✅ **Entity List** - jump directly to any entity |
| 😤 **Getting local_keys** | Manual copy-paste from Tuya IoT | ✅ **Cloud Sync** - one click fetches all keys |
| 😤 **HA 2025.x errors** | Breaking changes, crashes | ✅ **Fully compatible** and tested |
| 😤 **Can't run both versions** | Must choose one | ✅ **Parallel install** - test without risk |

> **💡 Bottom line:** We fixed the daily frustrations that LocalTuya users know too well.

---

## ✨ Features

### 🚀 Quick Edit (v6.0)
Change host, local_key, or protocol version **without** reconfiguring all entities:

```
Settings → Devices → LocalTuya 2.0 → Configure
→ Select device → Quick edit (host, key, protocol)
→ Change what you need → Done!
```

### ☁️ Cloud Key Sync (v6.0)
Automatically fetch local_keys for **all devices** with one click:
- No more manual copy-paste from Tuya IoT Platform
- Shows which keys have changed
- Updates only modified keys

### 🔄 Parallel Installation
Run alongside original LocalTuya:
- Different domain (`localtuya_bildass`)
- Test before migrating
- No conflicts

### 🛠️ Enhanced Cloud API
- **Async aiohttp** instead of blocking requests
- **Token caching** - fewer API calls
- **Pagination** - supports 100+ devices
- **HMAC-SHA256** with proper nonce handling

---

## 📦 Installation

### HACS (Recommended)

1. Open HACS → **Integrations**
2. Click **⋮** (three dots) → **Custom repositories**
3. Add: `https://github.com/Bildass/localtuya`
4. Category: **Integration**
5. Find **LocalTuya 2.0** and click **Download**
6. **Restart Home Assistant**

### Manual Installation

```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git temp_localtuya
mv temp_localtuya/custom_components/localtuya_bildass .
rm -rf temp_localtuya
# Restart Home Assistant
```

---

## 🔄 Migration Guide

### From Original LocalTuya

**Good news:** You can run both versions simultaneously! And you **don't need to re-fetch local_keys** - they're already in your config!

#### Quick Overview

1. **Install LocalTuya 2.0** via HACS (don't remove original yet)
2. **Export your existing device data** (see below)
3. **Add the integration:** Settings → Devices & Services → Add → **LocalTuya 2.0**
4. **Re-add devices** using your exported data (no Cloud API needed!)
5. **Test everything works**
6. **Remove original LocalTuya** when satisfied

---

### 📋 Step 1: Export Your Existing Configuration

Your existing device configurations (including precious `local_key` values) are stored in Home Assistant's config storage. Here's how to extract them:

#### Option A: Python Script (Recommended for 10+ devices)

Create a file called `export_localtuya.py` in your Home Assistant `/config` directory:

```python
#!/usr/bin/env python3
"""Export LocalTuya device configurations for migration to LocalTuya 2.0"""

import json
from pathlib import Path

# Read config entries
config_path = Path('/config/.storage/core.config_entries')
with open(config_path, 'r') as f:
    data = json.load(f)

# Find LocalTuya entries
devices = []
for entry in data['data']['entries']:
    domain = entry.get('domain', '').lower()
    if domain == 'localtuya':
        device_data = entry.get('data', {})
        devices.append({
            'name': entry.get('title', 'Unknown'),
            'device_id': device_data.get('device_id'),
            'local_key': device_data.get('local_key'),
            'host': device_data.get('host'),
            'protocol_version': device_data.get('protocol_version', '3.3'),
            'entities': device_data.get('entities', [])
        })

# Save to file
output_path = Path('/config/localtuya_export.json')
with open(output_path, 'w') as f:
    json.dump(devices, f, indent=2)

print(f"✅ Exported {len(devices)} devices to {output_path}")
print("\nDevices found:")
for d in devices:
    print(f"  - {d['name']}: {d['device_id'][:8]}... @ {d['host']}")
```

Run it via SSH or Terminal add-on:
```bash
cd /config
python3 export_localtuya.py
```

#### Option B: Manual Export (Few devices)

1. Access your Home Assistant via SSH or File Editor
2. Open `/config/.storage/core.config_entries`
3. Search for `"domain": "localtuya"`
4. Copy the relevant entries to a text file

---

### 📝 Step 2: Identify Key Information

For each device, you need:

| Field | Where to Find | Example |
|-------|---------------|---------|
| `device_id` | Exported data / Tuya IoT | `bf123456789abcdef` |
| `local_key` | **Exported data** (don't re-fetch!) | `abcd1234efgh5678` |
| `host` | Exported data / Router DHCP | `192.168.1.100` |
| `protocol_version` | Exported data (usually 3.3 or 3.4) | `3.3` |
| `entities` | Exported data (DP configurations) | switches, sensors, etc. |

> **💡 Pro tip:** The `local_key` is the most valuable piece - it's tedious to get from Tuya Cloud. Your export file already has it!

---

### 🔧 Step 3: Add Devices to LocalTuya 2.0

For each device in your export:

1. Go to **Settings → Devices & Services → LocalTuya 2.0 → Configure**
2. Select **Add new device**
3. Enter the device details from your export:
   - **Device ID:** Copy from export
   - **Host:** Copy from export (or use new IP if changed)
   - **Local Key:** Copy from export
   - **Protocol Version:** Copy from export
4. Configure entities using the DP numbers from your export
5. Repeat for all devices

> **⏱️ Time estimate:** ~2-3 minutes per device with prepared data

---

### 🚀 Step 4: Use Cloud Sync (Alternative Method)

If you have Tuya Cloud API configured, you can speed this up:

1. **Configure Cloud API** in LocalTuya 2.0:
   - Go to Settings → Devices & Services → LocalTuya 2.0 → Configure
   - Select "Reconfigure Cloud API account"
   - Enter your Tuya IoT credentials

2. **Use Cloud Sync:**
   - When adding a device, LocalTuya 2.0 will auto-fill `device_id` and `local_key`
   - You still need to configure entities manually (DPs)

---

### ⚠️ Entity Name Changes

Your entity IDs will change after migration:

| Original | LocalTuya 2.0 |
|----------|-------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |
| `climate.localtuya_xxx` | `climate.localtuya_bildass_xxx` |

**Important:** Update these in:
- ✏️ Automations
- ✏️ Scripts
- ✏️ Dashboard cards
- ✏️ Template sensors
- ✏️ Groups

---

### ✅ Step 5: Verify and Clean Up

1. **Test all devices** in LocalTuya 2.0
2. **Check automations** still work
3. **Once satisfied**, remove original LocalTuya:
   - Settings → Devices & Services → LocalTuya → Delete

---

### 💡 Migration Tips

- **Set static IPs** for your Tuya devices in your router to prevent IP changes
- **Export before updating** Home Assistant - config format might change
- **Keep the export file** as backup - local_keys are hard to get again
- **Migrate in batches** if you have many devices - test each batch before continuing
- **Use device names** from your export to keep things organized

---

## 📖 Documentation

### Initial Setup

1. **Add Integration:** Settings → Devices & Services → Add Integration → **LocalTuya 2.0**

2. **Configure Cloud API** (recommended):
   - Get credentials from [Tuya IoT Platform](https://iot.tuya.com)
   - **Region:** eu / us / cn / in
   - **Client ID:** Cloud → Development → Overview
   - **Client Secret:** Same location
   - **User ID:** From "Link Tuya App Account"

3. **Add Devices:** Use Cloud Sync or manual configuration

### Supported Devices

| Type | Examples |
|------|----------|
| **Switches** | Smart plugs, relays, power strips |
| **Lights** | Bulbs, LED strips, dimmers |
| **Covers** | Blinds, shades, curtains, garage doors |
| **Fans** | Ceiling fans, air purifiers |
| **Climate** | Thermostats, AC controllers, heaters |
| **Vacuums** | Robot vacuums |
| **Sensors** | Temperature, humidity, motion, door/window |
| **Numbers** | Brightness, speed, temperature setpoints |
| **Selects** | Modes, presets |

**Supported Protocols:** 3.1, 3.2, 3.3, 3.4

### Energy Monitoring

For devices with power measurement:

```yaml
sensor:
  - platform: template
    sensors:
      smart_plug_voltage:
        friendly_name: "Smart Plug Voltage"
        value_template: "{{ state_attr('switch.my_smart_plug', 'voltage') }}"
        unit_of_measurement: 'V'
        device_class: voltage
      smart_plug_current:
        friendly_name: "Smart Plug Current"
        value_template: "{{ state_attr('switch.my_smart_plug', 'current') }}"
        unit_of_measurement: 'mA'
        device_class: current
      smart_plug_power:
        friendly_name: "Smart Plug Power"
        value_template: "{{ state_attr('switch.my_smart_plug', 'current_consumption') }}"
        unit_of_measurement: 'W'
        device_class: power
```

### Debugging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

Also enable **"Enable debugging for this device"** in device configuration.

---

## 📋 Changelog

### v6.0.0 - Config Flow Revolution
- ✨ **Quick Edit** - change host/local_key/protocol without entities
- ✨ **Entity List** - direct editing of single entity
- ✨ **Cloud Sync** - fetch all local_keys with one click
- ✨ **Device Actions Menu** - new organized submenu
- 🔧 **Async Cloud API** - aiohttp, token caching, pagination
- 🔧 **Security** - HMAC-SHA256 with proper nonce

### v5.5.0
- 🗑️ Removed non-functional QR authentication
- 🔧 Simplified config flow

### v5.4.0
- ✨ Parallel installation alongside original LocalTuya
- 🔧 Changed domain to `localtuya_bildass`

### v5.3.1
- 🐛 Home Assistant 2025.x compatibility fixes

---

## 🆚 Comparison with Original

| Feature | Original LocalTuya | LocalTuya 2.0 |
|---------|:------------------:|:-----------:|
| Quick Edit (IP/key change) | ❌ | ✅ |
| Direct entity editing | ❌ | ✅ |
| One-click cloud key sync | ❌ | ✅ |
| HA 2025.x compatible | ⚠️ Issues | ✅ |
| Parallel installation | ❌ | ✅ |
| Async cloud API | ❌ | ✅ |
| 100+ device support | ⚠️ Limited | ✅ |
| Active development | ⚠️ Slow | ✅ |

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support & Contact

- 🌐 **Website:** [bildassystem.cz](https://bildassystem.cz)
- 📧 **Email:** info@bildassystem.cz
- 🐛 **Issues:** [GitHub Issues](https://github.com/Bildass/localtuya/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/Bildass/localtuya/discussions)

---

## 🙏 Credits

Built upon the excellent work of:
- [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) - Original project
- [NameLessJedi](https://github.com/NameLessJedi), [mileperhour](https://github.com/mileperhour), [TradeFace](https://github.com/TradeFace) - Code foundation
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - Protocol 3.4 implementation

---

<p align="center">
  <strong>LocalTuya 2.0</strong><br>
  © 2024-2025 <a href="https://bildassystem.cz">BildaSystem.cz</a><br>
  <sub>Fork of <a href="https://github.com/rospogrigio/localtuya">rospogrigio/localtuya</a> • Licensed under GPL-3.0</sub>
</p>
