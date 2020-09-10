[![](https://img.shields.io/github/release/rospogrigio/localtuya-homeassistant/all.svg?style=for-the-badge)](https://github.com/rospogrigio/localtuya-homeassistant/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![](https://img.shields.io/badge/MAINTAINER-%40rospogrigio-green?style=for-the-badge)](https://github.com/rospogrigio)

# localtuya-homeassistant

Local handling for Tuya Switches under Home-Assistant and Hassio, getting parameters from them (as Power Meters: Voltage, Current, Watt). Supports 3 types of switches: one-gang switches, two-gang switches and wifi plug (with additional USB plugs).

Also introduced handling for Tuya Covers and Lights, introducing pytuya library 7.1.0 that finally handles the 'json obj data unvalid' error correctly.

Developed substantially by merging the codes of NameLessJedi, mileperhour and TradeFace (see Thanks paragraph).

# How it works:

   1. Copy the localtuya folder content, and pytuya handler folder, to /custom_components/localtuya/ folder, inside /config folder (via Samba for HASSIO).
   
   2. Identify on your Home-Assistant logs (putting your logging into debug mode), the different attributes you want to handle by HA.

   3. Find in the switch.py file that part, and edit it for ID/DPS that is correct for your device.
```
          @property
          def device_state_attributes(self):
            attrs = {}
            try:
                attrs[ATTR_CURRENT] = "{}".format(self._status['dps']['104'])
                attrs[ATTR_CURRENT_CONSUMPTION] = "{}".format(self._status['dps']['105']/10)
                attrs[ATTR_VOLTAGE] = "{}".format(self._status['dps']['106']/10)
            except KeyError:
                pass
            return attrs
```
   NOTE: Original data from the device for Voltage and Watt, includes the first decimal. So if the value is 2203, the correct value is 220,3V. By this reason, this values are divided by 10 ('/10' in the script). While Current is sent in mA (int number, no decimals), so it don't need any conversion factor to be added on the declaration.

   4. Use this declaration on your configuration.yaml file (you need to get the 'device_id' and 'local_key' parameters for your device, as it can be obtained on other tutorials on the web:
```
##### FOR ONE-GANG SWITCHES #####
switch:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: tuya_01
    protocol_version: 3.3
    current: 18
    current_consumption: 19
    voltage: 20

##### FOR TWO-GANG SWITCHES / PLUGS #####
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: tuya_01
    protocol_version: 3.3
    switches:
      sw01:
        name: main_plug
        friendly_name: Main Plug
        id: 1
        current: 18
        current_consumption: 19
        voltage: 20
      sw02:
        name: usb_plug
        friendly_name: USB Plug
        id: 7  
```
   NOTE: (as many switch declared as the device has, take note that: If your device is composed (ex. one switch with a independent led light in it), this led can be declared as a 'switch'. ¡This Python script does not include RGB handling! (RGB Handling is independent and must be declared as a 'light' custom device, you can search web for examples, but i have not test this). 
   
   NOTE2: for each switch/subswitch both name and friendly_name must be specified: name will be used as the entity ID, while friendly_name will be used as the name in the frontend.
      
   5. Use this declaration on your configuration.yaml file, for stating sensors that handle its attributes:
```   
       sensor:
         - platform: template
           sensors:
             tuya-sw01_voltage:
               value_template: >-
                 {{ states.switch.sw01.attributes.voltage }}
               unit_of_measurement: 'V' 
             tuya-sw01_current:
               value_template: >-     
                 {{ states.switch.sw01.attributes.current }}
               unit_of_measurement: 'mA'      
             tuya-sw01_current_consumption:
               value_template: >-
                 {{ states.switch.sw01.attributes.current_consumption }}
               unit_of_measurement: 'W' 
```               
   6. If all gone OK (your device's parameters local_key and device_id are correct), your switch is working, so the sensors are working too.
   
   NOTE: You can do as changes as you want in scripts ant/or yaml files. But: You can't declare your "custom_component" as "tuya", tuya is a forbidden word from 0.88 version or so. So if you declare a switch.tuya, the embedded (cloud based) Tuya component will be load instead custom_component one.
   
   7. If you are using a cover device, this is the configuration to be used (as explained in cover.py):
```   
cover:
  - platform: localtuya
    host: 192.168.0.123
    local_key: 1234567891234567
    device_id: 123456789123456789abcd
    name: cover_guests
    friendly_name: Cover guests
    protocol_version: 3.3
    id: 1
```   
    
# To-do list:

   Create a (good and precise) sensor (counter) for Energy (kWh) -not just Power, but based on it-. 
      Ideas: Use: https://www.home-assistant.io/components/integration/ and https://www.home-assistant.io/components/utility_meter/
   
   RGB integration (for devices integrating both plug switch, power meter, and led light) 
   
   Create a switch for cover backlight (dps 101): pytuya library already supports it
   
   climate (thermostats) devices handling
   

# Thanks to:

NameLessJedi https://github.com/NameLessJedi/localtuya-homeassistant and mileperhour https://github.com/mileperhour/localtuya-homeassistant being the major sources of inspiration, and whose code for switches is substantially unchanged.

TradeFace, for being the only one to provide the correct code for communication with the cover (in particular, the 0x0d command for the status instead of the 0x0a, and related needs such as double reply to be received): https://github.com/TradeFace/tuya/

sean6541, for the working (standard) Python Handler for Tuya devices.
