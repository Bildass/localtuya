---
name: Device Template Request
about: Request a new device template to be added to LocalTuya BildaSystem
title: 'Template Request: [Device Name]'
labels: 'template-request'
assignees: ''

---

## Device Information

**Device Name/Model:**
<!-- e.g., "Generic Ceiling Fan", "Inkbird ITC-308-WIFI" -->

**Product Link (optional):**
<!-- Amazon, AliExpress, or manufacturer link -->

**Device Category:**
<!-- e.g., light, switch, fan, climate, sensor, cover, vacuum, etc. -->

---

## Required Information

### 1. Product ID (REQUIRED)
<!--
  This is the most important piece of information!

  How to find it:
  1. Go to https://iot.tuya.com/
  2. Navigate to: Cloud → Development → Your Project → Devices
  3. Click on your device
  4. Copy the "Product ID" (looks like: abcd1234xyz5678)
-->
**Product ID:**

### 2. Device DPS (Data Points)
<!--
  Provide the DPS values from your device. You can get them by:

  Option A - Home Assistant Developer Tools:
  1. Go to Developer Tools → States
  2. Find your LocalTuya entity
  3. Look at the attributes, find "dps"

  Option B - Tuya IoT Platform:
  1. Go to your device in Tuya IoT Platform
  2. Use "Device Debugging" feature
  3. Click "Get Device Status"

  Paste the full DPS dump below:
-->
```json
{
  "1": true,
  "2": 50,
  "3": "white"
}
```

### 3. DPS Descriptions (REQUIRED)
<!--
  Describe what each DPS does. This is crucial for creating the template!
  Test each DPS in the Tuya app or through debugging.
-->

| DPS | Type | Values | Description |
|-----|------|--------|-------------|
| 1 | boolean | true/false | Power on/off |
| 2 | integer | 0-100 | Brightness |
| 3 | string | "white"/"colour" | Light mode |

### 4. Protocol Version (if known)
<!--
  Usually 3.3, 3.4, or 3.5
  You can find this in LocalTuya device configuration or device logs
-->
**Protocol:**

---

## Screenshots
<!--
  Screenshots help us understand your device better!
  Please attach screenshots of:

  - [ ] Tuya IoT Platform device page (showing Product ID)
  - [ ] Device Debugging page (showing available DPS)
  - [ ] Tuya/Smart Life app showing device controls (optional)
-->

---

## Additional Information
<!--
  Any other details that might help:
  - Does this device work with the official Tuya cloud integration?
  - Did it work with previous versions of LocalTuya?
  - Any special features or modes?
-->

---

## Checklist

- [ ] I have provided the Product ID
- [ ] I have provided the DPS values
- [ ] I have described what each DPS does
- [ ] I have read the [README](../../README.md) and checked existing templates
