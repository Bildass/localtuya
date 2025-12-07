# LocalTuya BildaSystem

🇬🇧 **English** | [🇨🇿 Čeština](README.cs.md)

> **Actively maintained fork by [BildaSystem.cz](https://bildassystem.cz)**

Fork of [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) with improved config flow, automatic cloud key retrieval, and Home Assistant 2025.x compatibility.

---

## Key Advantages Over Original LocalTuya

| Feature | Original | BildaSystem |
|---------|----------|-------------|
| Quick Edit (change IP/key) | Click through all entities | Single window, done |
| Entity editing | Must go through all | Select specific one |
| Cloud key sync | Manual copying | One click |
| HA 2025.x compatibility | Errors | Works |
| Parallel installation | No | Yes (different domain) |

---

## Installation

### HACS (recommended)
1. HACS → Integrations → Custom repositories
2. Add `https://github.com/Bildass/localtuya`
3. Install "LocalTuya BildaSystem"
4. Restart Home Assistant

### Manual Installation
```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git
mv localtuya/custom_components/localtuya_bildass .
rm -rf localtuya
```

---

## Configuration

### 1. Add Integration
Settings → Devices & Services → Add Integration → **LocalTuya BildaSystem**

### 2. Cloud API (recommended)
Enter credentials from [Tuya IoT Platform](https://iot.tuya.com):
- **Region** - eu/us/cn/in
- **Client ID** - from Cloud → Development → Overview
- **Client Secret** - same location
- **User ID** - from Link Tuya App Account

> Without Cloud API, you must enter local_key manually.

### 3. Main Menu
After configuration you'll see:
- **Add a new device** - add device
- **Edit a device** - edit existing
- **Sync local keys from cloud** - fetch keys from cloud
- **Reconfigure Cloud API** - change cloud credentials

### 4. Quick Edit (NEW in v6.0)
When editing a device:
1. Select device
2. Choose **Quick edit (host, key, protocol)**
3. Change what you need
4. Done - no clicking through entities!

### 5. Sync from Cloud (NEW in v6.0)
Automatically fetches local_keys for all devices:
1. Main menu → **Sync local keys from cloud**
2. Shows which keys have changed
3. Confirm → keys are updated

---

## Supported Devices

- Switches
- Lights
- Covers (blinds, shades)
- Fans
- Climates (thermostats, AC)
- Vacuums
- Sensors
- Numbers
- Selects

**Protocols:** 3.1, 3.2, 3.3, 3.4

---

## Energy Monitoring

For devices with power monitoring, you can create template sensors:

```yaml
sensor:
  - platform: template
    sensors:
      tuya_voltage:
        value_template: "{{ states.switch.my_switch.attributes.voltage }}"
        unit_of_measurement: 'V'
      tuya_current:
        value_template: "{{ states.switch.my_switch.attributes.current }}"
        unit_of_measurement: 'mA'
      tuya_power:
        value_template: "{{ states.switch.my_switch.attributes.current_consumption }}"
        unit_of_measurement: 'W'
```

---

## Debugging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

Then check **Enable debugging for this device** when editing a device.

---

## Changelog

### v6.0.0 (Current)
- **Major Config Flow Overhaul**
  - Quick Edit - change host/local_key/protocol without entities
  - Entity List - direct editing of single entity
  - Sync from Cloud - fetch keys with one click
  - Device Actions Menu - new submenu
- **Enhanced Cloud API**
  - Async aiohttp instead of requests
  - Token caching
  - Pagination for 100+ devices
  - HMAC-SHA256 with nonce

### v5.5.0
- Removed non-functional QR authentication
- Simplified config flow

### v5.4.0
- Parallel installation alongside original LocalTuya
- Changed domain to `localtuya_bildass`

### v5.3.1
- HA 2025.x compatibility fixes

---

## Contact

- Web: [bildassystem.cz](https://bildassystem.cz)
- Email: info@bildassystem.cz
- GitHub: [Bildass/localtuya](https://github.com/Bildass/localtuya)
- Issues: [GitHub Issues](https://github.com/Bildass/localtuya/issues)

---

## Development

### Release Workflow

HACS uses Git tags for version display. Without tags, it shows commit hashes.

```bash
cd /home/core/projects/localtuya

# 1. Update version in manifest.json
#    custom_components/localtuya_bildass/manifest.json
#    "version": "6.1.0"

# 2. Commit changes
git add .
git commit -m "v6.1.0: Description of changes"

# 3. Create tag (must match manifest version)
git tag v6.1.0 -m "v6.1.0: Description of changes"

# 4. Push everything
git push origin master
git push origin v6.1.0
```

**Optional:** Create a GitHub Release from the tag for nicer release notes.

---

## Credits

Based on work by:
- [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) - original project
- [NameLessJedi](https://github.com/NameLessJedi), [mileperhour](https://github.com/mileperhour), [TradeFace](https://github.com/TradeFace) - code foundation
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - protocol 3.4

---

*LocalTuya BildaSystem © 2024-2025 [BildaSystem.cz](https://bildassystem.cz) | Fork of [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) (GPL-3.0)*
