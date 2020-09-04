
# localtuya-homeassistant

A Home Assistant / Hass.io add-on for local handling of Tuya-based devices.

The following Tuya device types are currently supported:
* 1 gang switches
* 2 gang switches
* Wi-Fi plugs (including those with additional USB plugs)
* Lights
* Covers

Energy monitoring (voltage, current, watts, etc.) is supported for compatible devices. 

This repository was substantially developed by utilizing and merging code from NameLessJedi, mileperhour and TradeFace. Refer to the "Thanks to" section below.

# Installation:

Copy the localtuya folder and all of its contents into your Home Assistant's custom_components folder. This is often located inside of your /config folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at /usr/share/hassio/homeassistant. It is possible that your custom_components folder does not exist. If that is the case, create the folder in the proper location, and then copy the localtuya folder and all of its contents inside the newly created custom_components folder.

Alternatively, you can install localtuya through HACS by adding this repository.


# Usage:

**NOTE: You must have your Tuya device's Key and ID in order to use localtuya. Follow the instructions here (https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md) if you still need your Key and ID.**

1. Add the proper entry to your configuration.yaml file. Several example configurations for different device types are provided below. Make sure to save when you are finished editing configuration.yaml.

```
   #### 1 GANG SWITCH ####
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
```

```
    ##### 2 GANG SWITCH / PLUG #####
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

```
   #### COVER ####
   cover:
     - platform: localtuya #REQUIRED
       host: 192.168.0.123 #REQUIRED
       local_key: 1234567891234567 #REQUIRED
       device_id: 123456789123456789abcd #REQUIRED
       name: cover_guests #REQUIRED
       friendly_name: Cover guests #REQUIRED
       protocol_version: 3.3 #REQUIRED
       id: 1 #OPTIONAL
       icon: mdi:blinds #OPTIONAL
       open_cmd: open #OPTIONAL, default is 'on'
       close_cmd: close #OPTIONAL, default is 'off'
       stop_cmd: stop #OPTIONAL, default is 'stop'
```
   
2. Enable debug logging in your configuration.yaml file.
```
      #Logging
      logger:
        default: info
        logs:
          custom_components.localtuya: debug
```

3. Restart Home Assistant.

4. Wait until Home Assistant is fully loaded, then access your logs. If localtuya has succesfully connected to your device, you will see a "decrypted result" with all of your device's DPs. See below for a succesful connection log:
```
2020-09-04 02:08:26 DEBUG (SyncWorker_26) [custom_components.localtuya.pytuya] decrypted result='{"devId":"REDACTED","dps":{"1":"stop","2":100,"3":40,"5":false,"7":"closing","8":"cancel","9":0,"10":0}}'
```   
   
5. Make any necessary edits to the python file(s) for your device(s). For example, if you are using a switch device, you may want to edit switch.py to account for the IDs/DPs that are applciable to your specific device.
```
          #### switch.py snippet
          @property
          def device_state_attributes(self):
            attrs = {}
            try:
                attrs[ATTR_CURRENT] = "{}".format(self._status['dps']['104']) # Modify to match your device's DPs
                attrs[ATTR_CURRENT_CONSUMPTION] = "{}".format(self._status['dps']['105']/10) # Modify to match your device's DPs
                attrs[ATTR_VOLTAGE] = "{}".format(self._status['dps']['106']/10) # Modify to match your device's DPs
            except KeyError:
                pass
            return attrs
```

6. Add any applicable sensors, using the below configuration.yaml entry as a guide:
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

# Notes:

* Do not declare anything as "tuya", such as by initiating a "switch.tuya". Using "tuya" launches Home Assistant's built-in, cloud-based Tuya integration in lieu of localtuya.

* Raw data from Tuya devices for Voltage and Watts includes the first decimal. For example, if the value is 2203, then the correct value is 220,3V. Values are thus divided by 10 ('/10' in the script). Current, however, is sent in mA as an integer with no decimals, so it does not need any conversion factor added on to the declaration.

* If your device is composed (e.g. one switch with an independent LED light in it), this LED can be declared as a 'switch'. However, the Python script does not include RGB handling! In order to use RGB handling, it must be declared as a custom 'light device'. This has not been tested with localtuya, however it may be possible to make it work. Google is your friend. 
   
* For each switch and/or subswitch, name **and** friendly_name must be specified in configuration.yaml. Name will be used as the Entity ID, while friendly_name will be used as the name in the frontend.

# To-do list:

* Create a (good and precise) sensor (counter) for Energy (kWh) -not just Power, but based on it-. 
      Ideas: Use: https://www.home-assistant.io/components/integration/ and https://www.home-assistant.io/components/utility_meter/
   
* RGB integration (for devices integrating both plug switch, power meter, and led light) 
   
* Create a switch for cover backlight (dps 101): pytuya library already supports it

# Thanks to:

NameLessJedi https://github.com/NameLessJedi/localtuya-homeassistant and mileperhour https://github.com/mileperhour/localtuya-homeassistant being the major sources of inspiration, and whose code for switches is substantially unchanged.

TradeFace, for being the only one to provide the correct code for communication with the cover (in particular, the 0x0d command for the status instead of the 0x0a, and related needs such as double reply to be received): https://github.com/TradeFace/tuya/

sean6541, for the working (standard) Python Handler for Tuya devices.
