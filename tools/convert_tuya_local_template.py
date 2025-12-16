#!/usr/bin/env python3
"""
Tuya-Local to LocalTuya BildaSystem Template Converter

Converts device templates from tuya-local (make-all/tuya-local) YAML format
to our JSON format.

Usage:
    python convert_tuya_local_template.py <yaml_file_or_url>
    python convert_tuya_local_template.py amico_smart_ceiling_fan.yaml
    python convert_tuya_local_template.py https://raw.githubusercontent.com/make-all/tuya-local/main/custom_components/tuya_local/devices/amico_smart_ceiling_fan.yaml

Source: https://github.com/make-all/tuya-local (MIT License)
"""

import sys
import json
import yaml
import urllib.request
from pathlib import Path


# Mapping from tuya-local entity types to our platform names
ENTITY_TO_PLATFORM = {
    "fan": "fan",
    "light": "light",
    "switch": "switch",
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "climate": "climate",
    "cover": "cover",
    "number": "number",
    "select": "select",
    "vacuum": "vacuum",
    "humidifier": "humidifier",
    "water_heater": "water_heater",
    "siren": "siren",
    "lock": "lock",
    "button": "button",
    "alarm_control_panel": "alarm_control_panel",
}

# DPS name to our config key mapping
DPS_NAME_MAPPING = {
    "switch": "id",  # Main switch DPS
    "brightness": "brightness_dp",
    "color_temp": "color_temp_dp",
    "colour_data": "color_dp",
    "speed": "speed_dp",
    "preset_mode": "preset_mode_dp",
    "direction": "direction_dp",
    "oscillate": "oscillate_dp",
    "position": "position_dp",
    "current_position": "current_position_dp",
    "set_position": "set_position_dp",
    "temperature": "target_temp_dp",
    "current_temperature": "current_temp_dp",
    "hvac_mode": "hvac_mode_dp",
    "fan_mode": "fan_mode_dp",
    "humidity": "humidity_dp",
    "current_humidity": "current_humidity_dp",
}


def fetch_yaml(source: str) -> dict:
    """Fetch YAML from file or URL."""
    if source.startswith("http"):
        with urllib.request.urlopen(source) as response:
            content = response.read().decode("utf-8")
    else:
        with open(source, "r") as f:
            content = f.read()
    return yaml.safe_load(content)


def convert_dps_mapping(dps_list: list, entity_type: str) -> dict:
    """Convert tuya-local DPS list to our entity config."""
    config = {}

    for dps in dps_list:
        dps_id = dps.get("id")
        dps_name = dps.get("name", "")
        dps_type = dps.get("type", "")

        # Find the main switch/control DP
        if dps_name == "switch":
            config["id"] = dps_id
            continue

        # Map known DPS names to our config keys
        if dps_name in DPS_NAME_MAPPING:
            key = DPS_NAME_MAPPING[dps_name]
            if key != "id":  # Already handled above
                config[key] = dps_id

        # Handle ranges (for number entities, brightness, etc.)
        if "range" in dps:
            range_info = dps["range"]
            if "min" in range_info:
                config["min_value"] = range_info["min"]
            if "max" in range_info:
                config["max_value"] = range_info["max"]

        # Handle value mappings
        if "mapping" in dps:
            mappings = dps["mapping"]
            values = []
            for m in mappings:
                if "dps_val" in m and "value" in m:
                    values.append(str(m["dps_val"]))
            if values and dps_name in ["preset_mode", "hvac_mode", "fan_mode"]:
                config[f"{dps_name}s"] = values

    # If no main ID found, use first DPS
    if "id" not in config and dps_list:
        config["id"] = dps_list[0].get("id")

    return config


def convert_entity(entity: dict) -> dict:
    """Convert a single tuya-local entity to our format."""
    entity_type = entity.get("entity", "switch")
    platform = ENTITY_TO_PLATFORM.get(entity_type, entity_type)

    dps_list = entity.get("dps", [])

    # Start with basic config
    our_entity = {
        "platform": platform,
    }

    # Convert DPS configuration
    dps_config = convert_dps_mapping(dps_list, entity_type)
    our_entity.update(dps_config)

    # Add friendly name from translation key or entity type
    translation_key = entity.get("translation_key") or entity.get("translation_only_key")
    if translation_key:
        # Convert snake_case to Title Case
        friendly_name = translation_key.replace("_", " ").title()
    else:
        friendly_name = entity_type.replace("_", " ").title()
    our_entity["friendly_name"] = friendly_name

    # Handle device class if present
    if "class" in entity:
        our_entity["device_class"] = entity["class"]

    # Handle category (diagnostic, config, etc.)
    category = entity.get("category")
    if category == "diagnostic":
        our_entity["entity_category"] = "diagnostic"
    elif category == "config":
        our_entity["entity_category"] = "config"

    return our_entity


def convert_template(tuya_local: dict, source_file: str = "") -> dict:
    """Convert complete tuya-local template to our format."""

    # Get product info
    products = tuya_local.get("products", [])
    first_product = products[0] if products else {}

    product_key = first_product.get("id", "unknown")
    manufacturer = first_product.get("manufacturer", "Unknown")
    model = first_product.get("name", tuya_local.get("name", "Unknown Device"))

    # Convert entities
    entities = []
    for entity in tuya_local.get("entities", []):
        converted = convert_entity(entity)
        if converted.get("id"):  # Only add if we have a valid DPS ID
            entities.append(converted)

    # Build our template
    our_template = {
        "product_key": product_key,
        "name": tuya_local.get("name", model),
        "manufacturer": manufacturer,
        "model": model,
        "protocol_version": "3.3",  # Default, user may need to adjust
        "category": guess_category(tuya_local),
        "entities": entities,
        "source": "tuya-local (MIT License)",
        "source_file": source_file,
        "tested": False,
        "notes": "Auto-converted from tuya-local. May require manual adjustments."
    }

    # Add all product IDs if multiple
    if len(products) > 1:
        our_template["alternative_product_keys"] = [p.get("id") for p in products[1:]]

    return our_template


def guess_category(tuya_local: dict) -> str:
    """Guess device category from entities."""
    entities = tuya_local.get("entities", [])
    entity_types = [e.get("entity", "") for e in entities]

    if "climate" in entity_types:
        return "climate"
    elif "vacuum" in entity_types:
        return "vacuum"
    elif "cover" in entity_types:
        return "cover"
    elif "fan" in entity_types:
        if "light" in entity_types:
            return "fan_light"
        return "fan"
    elif "light" in entity_types:
        return "light"
    elif "humidifier" in entity_types:
        return "humidifier"
    elif "water_heater" in entity_types:
        return "water_heater"
    else:
        return "switch"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable templates: https://github.com/make-all/tuya-local/tree/main/custom_components/tuya_local/devices")
        sys.exit(1)

    source = sys.argv[1]

    # If just filename, construct full URL
    if not source.startswith("http") and not Path(source).exists():
        source = f"https://raw.githubusercontent.com/make-all/tuya-local/main/custom_components/tuya_local/devices/{source}"
        print(f"Fetching: {source}")

    try:
        tuya_local = fetch_yaml(source)
    except Exception as e:
        print(f"Error loading template: {e}")
        sys.exit(1)

    # Extract filename for reference
    source_file = source.split("/")[-1] if "/" in source else source

    # Convert
    our_template = convert_template(tuya_local, source_file)

    # Output
    output_filename = source_file.replace(".yaml", ".json")
    output_path = Path(__file__).parent.parent / "custom_components" / "localtuya_bildass" / "devices" / output_filename

    print("\n" + "=" * 60)
    print("CONVERTED TEMPLATE")
    print("=" * 60)
    print(json.dumps(our_template, indent=2, ensure_ascii=False))
    print("=" * 60)

    # Ask to save
    print(f"\nOutput path: {output_path}")
    if input("\nSave to devices folder? [y/N]: ").lower() == "y":
        with open(output_path, "w") as f:
            json.dump(our_template, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {output_path}")
        print("\nRemember to:")
        print("1. Review and adjust the template")
        print("2. Test with actual device")
        print("3. Update protocol_version if needed (3.3, 3.4, or 3.5)")
    else:
        print("\nTemplate printed above. Copy and adjust as needed.")


if __name__ == "__main__":
    main()
