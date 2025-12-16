#!/usr/bin/env python3
"""
Search Tuya-Local Device Templates

Searches through 995+ device templates from tuya-local repository.

Usage:
    python search_tuya_local.py <keyword>
    python search_tuya_local.py ceiling fan
    python search_tuya_local.py pet feeder
    python search_tuya_local.py dehumidifier

Source: https://github.com/make-all/tuya-local (MIT License)
"""

import sys
import json
import urllib.request


DEVICES_API = "https://api.github.com/repos/make-all/tuya-local/contents/custom_components/tuya_local/devices"


def fetch_device_list() -> list:
    """Fetch list of all device template files."""
    req = urllib.request.Request(
        DEVICES_API,
        headers={"Accept": "application/vnd.github.v3+json"}
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    # Filter only YAML files
    return [f["name"] for f in data if f["name"].endswith(".yaml")]


def search_templates(keywords: list, devices: list) -> list:
    """Search device names for keywords."""
    keywords_lower = [k.lower() for k in keywords]
    matches = []

    for device in devices:
        device_lower = device.lower()
        # Check if ALL keywords match
        if all(kw in device_lower for kw in keywords_lower):
            matches.append(device)

    return sorted(matches)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    keywords = sys.argv[1:]
    print(f"Searching for: {' '.join(keywords)}")
    print("Fetching device list...")

    try:
        devices = fetch_device_list()
        print(f"Found {len(devices)} device templates\n")
    except Exception as e:
        print(f"Error fetching device list: {e}")
        sys.exit(1)

    matches = search_templates(keywords, devices)

    if matches:
        print(f"Found {len(matches)} matching templates:")
        print("-" * 50)
        for i, device in enumerate(matches, 1):
            print(f"{i:3}. {device}")
        print("-" * 50)
        print(f"\nTo convert a template, run:")
        print(f"  python tools/convert_tuya_local_template.py <filename>")
        print(f"\nExample:")
        print(f"  python tools/convert_tuya_local_template.py {matches[0]}")
    else:
        print("No matching templates found.")
        print("\nTry broader search terms or check:")
        print("https://github.com/make-all/tuya-local/tree/main/custom_components/tuya_local/devices")


if __name__ == "__main__":
    main()
