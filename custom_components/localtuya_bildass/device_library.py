"""Device Library for LocalTuya BildaSystem.

This module provides auto-detection and entity configuration
based on pre-defined device profiles in the devices/ folder.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Cache for loaded device definitions
_device_library: dict[str, dict] = {}
_library_loaded: bool = False


def get_devices_path() -> Path:
    """Get the path to the devices folder."""
    return Path(__file__).parent / "devices"


def load_device_library() -> dict[str, dict]:
    """Load all device definitions from the devices/ folder.

    Returns a dictionary indexed by product_key.
    """
    global _device_library, _library_loaded

    if _library_loaded:
        return _device_library

    devices_path = get_devices_path()

    if not devices_path.exists():
        _LOGGER.warning("Device library folder not found: %s", devices_path)
        return {}

    _device_library = {}

    for json_file in devices_path.glob("*.json"):
        # Skip schema file
        if json_file.name.startswith("_"):
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                device_def = json.load(f)

            product_key = device_def.get("product_key")
            if product_key:
                _device_library[product_key] = device_def
                _LOGGER.debug(
                    "Loaded device definition: %s (%s)",
                    device_def.get("name"),
                    product_key
                )
            else:
                _LOGGER.warning("No product_key in %s", json_file.name)

        except json.JSONDecodeError as e:
            _LOGGER.error("Invalid JSON in %s: %s", json_file.name, e)
        except Exception as e:
            _LOGGER.error("Error loading %s: %s", json_file.name, e)

    _library_loaded = True
    _LOGGER.info("Device library loaded: %d device definitions", len(_device_library))

    return _device_library


def get_device_config(product_key: str) -> dict | None:
    """Get device configuration by product_key.

    Args:
        product_key: The Tuya product key to look up.

    Returns:
        Device configuration dict or None if not found.
    """
    library = load_device_library()
    return library.get(product_key)


def get_all_devices() -> list[dict]:
    """Get all device definitions as a list.

    Returns:
        List of all device configuration dicts.
    """
    library = load_device_library()
    return list(library.values())


def get_device_names() -> dict[str, str]:
    """Get mapping of product_key to device name.

    Returns:
        Dict mapping product_key -> device name.
    """
    library = load_device_library()
    return {pk: dev.get("name", "Unknown") for pk, dev in library.items()}


def get_entities_for_device(product_key: str) -> list[dict]:
    """Get entity configurations for a device.

    Args:
        product_key: The Tuya product key.

    Returns:
        List of entity configuration dicts.
    """
    device = get_device_config(product_key)
    if device:
        return device.get("entities", [])
    return []


def get_protocol_version(product_key: str) -> str | None:
    """Get recommended protocol version for a device.

    Args:
        product_key: The Tuya product key.

    Returns:
        Protocol version string or None.
    """
    device = get_device_config(product_key)
    if device:
        return device.get("protocol_version")
    return None


def search_devices(query: str) -> list[dict]:
    """Search devices by name, manufacturer, or model.

    Args:
        query: Search string (case-insensitive).

    Returns:
        List of matching device definitions.
    """
    library = load_device_library()
    query_lower = query.lower()

    results = []
    for device in library.values():
        name = device.get("name", "").lower()
        manufacturer = device.get("manufacturer", "").lower()
        model = device.get("model", "").lower()

        if query_lower in name or query_lower in manufacturer or query_lower in model:
            results.append(device)

    return results


def get_library_stats() -> dict:
    """Get statistics about the device library.

    Returns:
        Dict with library statistics.
    """
    library = load_device_library()

    manufacturers = set()
    categories = set()
    total_entities = 0

    for device in library.values():
        manufacturers.add(device.get("manufacturer", "Unknown"))
        categories.add(device.get("category", "unknown"))
        total_entities += len(device.get("entities", []))

    return {
        "total_devices": len(library),
        "manufacturers": sorted(manufacturers),
        "categories": sorted(categories),
        "total_entities": total_entities,
    }


def reload_library() -> None:
    """Force reload of the device library."""
    global _device_library, _library_loaded
    _device_library = {}
    _library_loaded = False
    load_device_library()
