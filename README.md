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
  <a href="#-why-localtuya-20">Why?</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation">Install</a> •
  <a href="#-roadmap">Roadmap</a> •
  <a href="#-documentation">Docs</a>
</p>

<p align="center">
  🇬🇧 <strong>English</strong> | <a href="README.cs.md">🇨🇿 Čeština</a>
</p>

---

## 🤔 Why LocalTuya 2.0?

The original [LocalTuya](https://github.com/rospogrigio/localtuya) was a game-changer for Tuya device owners. But development stalled, bugs piled up, and Home Assistant kept evolving. **We stepped in to keep LocalTuya alive.**

### The Problem

| Pain Point | What Happened |
|------------|---------------|
| 🐛 **HA 2024/2025 breaking changes** | Crashes, deprecation warnings, broken config flows |
| 🔧 **Protocol 3.5 devices** | Not supported, newer devices didn't work |
| 😤 **Changing device IP/key** | Click through ALL entities one by one |
| 📦 **No device templates** | Configure 15 DPs manually for every bulb |
| 🔐 **Complex cloud setup** | Need developer account, API keys, etc. |

### Our Solution

**LocalTuya 2.0** fixes all of this and more. We're committed to keeping local Tuya control **alive and thriving**.

> 💡 **Philosophy:** Your smart home should work **locally**, without cloud dependencies. That's why LocalTuya exists, and that's why we maintain it.

---

## ✨ Features

### 🆕 Protocol 3.5 Support (v7.0+)
Full support for the latest Tuya protocol:
- **GCM encryption** for secure communication
- **6699 packet prefix** handling
- **Proper heartbeat** with retry logic
- Works with newest Tuya devices

### 📚 Device Library (v7.0+)
Pre-configured templates for common devices:
- **Auto-detection** by product_id
- **One-click setup** - no manual DP configuration
- **Community templates** - growing library

Currently supported:
- Smart Mini Bulb RGB+CCT (Protocol 3.5)
- Smart Star Projector
- Tesla Air Purifier Mini
- Tesla Dehumidifier XL
- Tesla Power Strip PS300
- BlitzWolf Air Cleaner
- Nedis Pet Feeder
- KWS-302WF Energy Meter
- Circuit Breaker 63A
- Roleta M313EIRWT
- *...and more coming!*

### 🚀 Quick Edit
Change host, local_key, or protocol **without** reconfiguring entities:
```
Settings → Devices → LocalTuya 2.0 → Configure
→ Select device → Quick edit
→ Done in 10 seconds!
```

### ☁️ Cloud Key Sync
Fetch all local_keys with **one click**:
- No manual copy-paste from Tuya IoT
- Shows which keys changed
- Smart sync - only updates modified keys

### 🔄 Parallel Installation
Run alongside original LocalTuya:
- Different domain (`localtuya_bildass`)
- Test before migrating
- Zero conflicts

### 🌍 All Tuya Regions (v7.3.19+)
- EU - Central Europe
- EU West - Western Europe
- US - Western America
- US East - Eastern America
- CN - China
- IN - India
- **SG - Singapore** (new!)

---

## 📦 Installation

### HACS (Recommended)

1. Open HACS → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add: `https://github.com/Bildass/localtuya`
4. Category: **Integration**
5. Find **LocalTuya 2.0** → **Download**
6. **Restart Home Assistant**

### Manual

```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git temp
mv temp/custom_components/localtuya_bildass .
rm -rf temp
# Restart Home Assistant
```

---

## 🗺️ Roadmap

We're actively developing LocalTuya 2.0. Here's what's coming:

### 🔜 Coming Soon

| Feature | Status | Description |
|---------|--------|-------------|
| **QR Code Authentication** | 🔬 Research done | Login with Tuya app - no developer account needed! |
| **Water Heater Platform** | 📋 Planned | Support for smart kettles, water heaters |
| **More Device Templates** | 🔄 Ongoing | Community-contributed device configs |

### ✅ Recently Shipped

| Version | Feature |
|---------|---------|
| v7.3.20 | Fixed template name display in options flow |
| v7.3.19 | Added Singapore region + friendly region names |
| v7.3.18 | Heartbeat optimization + optimistic UI updates |
| v7.3.16 | Smart Mini Bulb template + product_id detection |
| v7.0.0 | Complete pytuya rewrite + Protocol 3.5 |

### 💡 Future Ideas

- **Matter bridge** - expose LocalTuya devices to Matter
- **Device diagnostics** - built-in network analyzer
- **Firmware version detection** - track device updates
- **Scenes support** - Tuya scene activation

> 📣 **Have a feature request?** [Open an issue](https://github.com/Bildass/localtuya/issues) or [start a discussion](https://github.com/Bildass/localtuya/discussions)!

---

## 📖 Documentation

### Quick Start

1. **Install** via HACS (see above)
2. **Add Integration:** Settings → Devices & Services → Add → **LocalTuya 2.0**
3. **Configure Cloud API** (optional but recommended):
   - Get credentials from [Tuya IoT Platform](https://iot.tuya.com)
   - Region, Client ID, Client Secret, User ID
4. **Add Devices:** Cloud Sync auto-fills device info!

### Supported Platforms

| Platform | Examples |
|----------|----------|
| **switch** | Smart plugs, relays, power strips |
| **light** | Bulbs, LED strips, dimmers |
| **cover** | Blinds, curtains, garage doors |
| **fan** | Ceiling fans, air purifiers |
| **climate** | Thermostats, AC controllers |
| **vacuum** | Robot vacuums |
| **sensor** | Temperature, humidity, power monitoring |
| **binary_sensor** | Motion, door/window, leak |
| **number** | Brightness, speed setpoints |
| **select** | Modes, presets |

### Supported Protocols

| Protocol | Encryption | Status |
|----------|------------|--------|
| 3.1 | AES-ECB | ✅ Supported |
| 3.2 | AES-ECB | ✅ Supported |
| 3.3 | AES-ECB | ✅ Supported |
| 3.4 | AES-GCM | ✅ Supported |
| **3.5** | AES-GCM | ✅ **Full Support** |

### Debugging

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

---

## 🔄 Migration from Original LocalTuya

**Good news:** You can run both versions simultaneously!

### Quick Steps

1. Install LocalTuya 2.0 via HACS
2. Export existing config (local_keys are precious!)
3. Add devices to LocalTuya 2.0
4. Test everything
5. Remove original when satisfied

### Entity Name Changes

| Original | LocalTuya 2.0 |
|----------|---------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Update references in:** Automations, Scripts, Dashboards, Templates

> 📚 **Full migration guide:** See [Migration Guide](#migration-guide) section below.

---

## 📋 Changelog

### v7.3.x - Stability & UX
- **v7.3.20** - Fix template name display in options flow
- **v7.3.19** - Add all Tuya regions (SG, EU West, US East) with friendly names
- **v7.3.18** - Heartbeat optimization, optimistic UI updates
- **v7.3.17** - Remove rate limiting (caused delays)
- **v7.3.16** - Smart Mini Bulb template, product_id detection fix

### v7.0.x - Protocol 3.5 Revolution
- **v7.0.0** - Complete pytuya rewrite, Protocol 3.5 support, Device Library

### v6.x - Config Flow Overhaul
- **v6.0.0** - Quick Edit, Entity List, Cloud Sync, Async API

<details>
<summary>📜 Older versions...</summary>

### v5.x
- **v5.5.0** - Removed broken QR auth, simplified flow
- **v5.4.0** - Parallel installation, domain change
- **v5.3.1** - HA 2025.x compatibility

</details>

---

## 🆚 Comparison

| Feature | Original LocalTuya | LocalTuya 2.0 |
|---------|:------------------:|:-------------:|
| Protocol 3.5 | ❌ | ✅ |
| Device templates | ❌ | ✅ |
| Quick Edit | ❌ | ✅ |
| Cloud Key Sync | ❌ | ✅ |
| HA 2024/2025 | ⚠️ Issues | ✅ |
| Parallel install | ❌ | ✅ |
| 100+ devices | ⚠️ Limited | ✅ |
| Active development | ❌ Stalled | ✅ **Active** |

---

## 🤝 Contributing

We welcome contributions!

### Ways to Help

- 🐛 **Report bugs** - [Open an issue](https://github.com/Bildass/localtuya/issues)
- 💡 **Request features** - [Start a discussion](https://github.com/Bildass/localtuya/discussions)
- 📚 **Add device templates** - Share your working configs
- 🌍 **Translations** - Help localize the integration
- 🔧 **Code** - PRs welcome!

### Development

```bash
git clone https://github.com/Bildass/localtuya.git
cd localtuya
# Create feature branch
git checkout -b feature/amazing-feature
# Make changes, commit, push
git push origin feature/amazing-feature
# Open PR
```

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
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - Protocol implementation
- [make-all/tuya-local](https://github.com/make-all/tuya-local) - Inspiration for QR auth research

**Community Contributors:**
- Everyone who reports bugs, suggests features, and shares device configs!

---

<p align="center">
  <strong>LocalTuya 2.0</strong><br>
  Keeping local Tuya control <strong>alive</strong>.<br><br>
  © 2024-2025 <a href="https://bildassystem.cz">BildaSystem.cz</a><br>
  <sub>Fork of <a href="https://github.com/rospogrigio/localtuya">rospogrigio/localtuya</a> • Licensed under GPL-3.0</sub>
</p>

---

<details>
<summary><h2>📚 Full Migration Guide</h2></summary>

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

Your existing device configurations (including precious `local_key` values) are stored in Home Assistant's config storage.

#### Option A: Python Script (Recommended for 10+ devices)

Create `export_localtuya.py` in `/config`:

```python
#!/usr/bin/env python3
"""Export LocalTuya device configurations for migration to LocalTuya 2.0"""

import json
from pathlib import Path

config_path = Path('/config/.storage/core.config_entries')
with open(config_path, 'r') as f:
    data = json.load(f)

devices = []
for entry in data['data']['entries']:
    if entry.get('domain', '').lower() == 'localtuya':
        device_data = entry.get('data', {})
        devices.append({
            'name': entry.get('title', 'Unknown'),
            'device_id': device_data.get('device_id'),
            'local_key': device_data.get('local_key'),
            'host': device_data.get('host'),
            'protocol_version': device_data.get('protocol_version', '3.3'),
            'entities': device_data.get('entities', [])
        })

output_path = Path('/config/localtuya_export.json')
with open(output_path, 'w') as f:
    json.dump(devices, f, indent=2)

print(f"✅ Exported {len(devices)} devices to {output_path}")
```

Run via SSH: `python3 /config/export_localtuya.py`

#### Option B: Manual (Few devices)

1. Open `/config/.storage/core.config_entries`
2. Search for `"domain": "localtuya"`
3. Copy relevant entries

---

### 📝 Step 2: Add Devices to LocalTuya 2.0

For each device:

1. **Settings → Devices & Services → LocalTuya 2.0 → Configure**
2. **Add new device**
3. Enter details from export: Device ID, Host, Local Key, Protocol
4. Configure entities using DP numbers from export
5. Repeat

> ⏱️ ~2-3 minutes per device with prepared data

---

### ⚠️ Entity Name Changes

Your entity IDs will change:

| Original | LocalTuya 2.0 |
|----------|---------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Update in:** Automations, Scripts, Dashboards, Templates, Groups

---

### 💡 Tips

- **Set static IPs** for Tuya devices in router
- **Keep export file** as backup
- **Migrate in batches** if many devices
- **Test each batch** before continuing

</details>

---

<details>
<summary><h2>⚡ Energy Monitoring Setup</h2></summary>

For devices with power measurement (smart plugs, power strips):

```yaml
# configuration.yaml
sensor:
  - platform: template
    sensors:
      smart_plug_voltage:
        friendly_name: "Smart Plug Voltage"
        value_template: "{{ state_attr('switch.localtuya_bildass_plug', 'voltage') }}"
        unit_of_measurement: 'V'
        device_class: voltage

      smart_plug_current:
        friendly_name: "Smart Plug Current"
        value_template: "{{ state_attr('switch.localtuya_bildass_plug', 'current') }}"
        unit_of_measurement: 'mA'
        device_class: current

      smart_plug_power:
        friendly_name: "Smart Plug Power"
        value_template: "{{ state_attr('switch.localtuya_bildass_plug', 'current_consumption') }}"
        unit_of_measurement: 'W'
        device_class: power
```

</details>
