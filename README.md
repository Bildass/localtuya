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

**Good news:** You can run both versions simultaneously!

1. **Install LocalTuya 2.0** via HACS (don't remove original yet)
2. **Add the integration:** Settings → Devices & Services → Add → **LocalTuya 2.0**
3. **Configure Cloud API** (optional but recommended)
4. **Re-add your devices** - with Cloud Sync, it's fast!
5. **Test everything works**
6. **Remove original LocalTuya** when satisfied

### Your Entities Will Change

| Original | LocalTuya 2.0 |
|----------|-------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Tip:** Update your automations, scripts, and dashboards after migration.

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
