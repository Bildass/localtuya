# How to Request a Device Template

This guide explains how to gather all the information needed to request a new device template for LocalTuya BildaSystem.

## What is a Device Template?

A device template is a pre-configured setup for a specific Tuya device type. It automatically maps the device's Data Points (DPS) to Home Assistant entities, so you don't have to configure them manually.

## Required Information

To create a template for your device, we need:

1. **Product ID** - Identifies your device type in Tuya's system
2. **DPS Values** - The data points your device uses
3. **DPS Descriptions** - What each data point does

---

## Step 1: Get Your Product ID

The Product ID is the most important piece of information. It identifies your exact device model.

### How to Find It:

1. **Log in to Tuya IoT Platform**
   - Go to [https://iot.tuya.com/](https://iot.tuya.com/)
   - Sign in with your developer account

2. **Navigate to Your Devices**
   - Click **Cloud** → **Development**
   - Select your project
   - Go to **Devices** tab
   - Click **Link Tuya App Account** if you haven't linked your devices yet

3. **Find the Product ID**
   - Click on your device in the list
   - Look for **Product ID** field
   - It looks like: `abcd1234xyz5678`

![Product ID Location](../img/product_id_example.png)
*(Screenshot placeholder - TODO: add actual screenshot)*

---

## Step 2: Get Device DPS (Data Points)

DPS are the control parameters of your device. Each DPS has a number and controls one aspect of the device.

### Method A: Tuya IoT Platform (Recommended)

1. In Tuya IoT Platform, go to your device
2. Click **Device Debugging**
3. Click **Get Device Status**
4. You'll see all available DPS with their current values

Example output:
```json
{
  "result": [
    {"code": "switch", "value": true},
    {"code": "fan_speed", "value": 3},
    {"code": "light_switch", "value": false}
  ]
}
```

### Method B: Home Assistant Developer Tools

1. In Home Assistant, go to **Developer Tools** → **States**
2. Search for your LocalTuya entity (e.g., `switch.living_room_fan`)
3. Look at the **Attributes** section
4. Find the `dps` attribute

### Method C: Enable Debug Logging

Add to your `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

Then check your Home Assistant logs for DPS updates when you control the device via the Tuya app.

---

## Step 3: Describe Each DPS

This is crucial! You need to tell us what each DPS does.

### How to Test DPS:

1. Use the Tuya IoT Platform **Device Debugging** feature
2. Send commands to individual DPS and observe what happens
3. Use the Tuya/Smart Life app and watch the logs for changes

### Example DPS Description Table:

| DPS | Code | Type | Range/Values | Description |
|-----|------|------|--------------|-------------|
| 1 | switch | Boolean | true/false | Main power switch |
| 2 | fan_speed | Integer | 1-6 | Fan speed level |
| 3 | light_switch | Boolean | true/false | Light on/off |
| 4 | brightness | Integer | 10-1000 | Light brightness |
| 5 | colour_data | String | HSV format | Light color (HSV) |
| 6 | work_mode | Enum | "white"/"colour"/"scene" | Light mode |
| 7 | countdown | Integer | 0-86400 | Auto-off timer (seconds) |

### Common DPS Types:

- **Boolean**: true/false (switches, toggles)
- **Integer**: Numbers with min/max range
- **Enum**: Predefined string values
- **String**: Text (often for color data, scenes)

---

## Step 4: Submit Your Request

1. Go to [GitHub Issues](https://github.com/Bildass/localtuya/issues)
2. Click **New Issue**
3. Select **Device Template Request**
4. Fill in all the required information
5. Attach screenshots if possible

---

## Tips for a Successful Request

- **Test thoroughly**: Know what each DPS does before submitting
- **Include screenshots**: Visual reference helps a lot
- **Check existing templates**: Your device might already be supported under a different name
- **Be patient**: Template creation takes time and testing

---

## Existing Templates

Before requesting, check if a similar device is already supported:

- Lights (bulbs, strips, various protocols)
- Switches and plugs
- Fans (with/without lights)
- Covers (blinds, curtains, garage doors)
- Climate (thermostats, AC controllers)
- Sensors (temperature, humidity, motion)
- Vacuums
- Pet feeders
- And more...

See [README.md](../README.md) for the full list of supported device types.

---

## Need Help?

If you're having trouble getting the information:

1. Check if your device is linked to Tuya IoT Platform
2. Make sure you're using the correct Tuya app (Tuya Smart or Smart Life)
3. Try the [TinyTuya](https://github.com/jasonacox/tinytuya) command-line tool

Feel free to ask questions in your issue - we're here to help!
