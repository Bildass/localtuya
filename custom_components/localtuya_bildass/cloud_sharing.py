"""Cloud sharing stub - QR code authentication removed.

QR code authentication was removed as it does not work with current
Smart Life / Tuya Smart app versions. Use the Tuya Developer Portal
credentials instead.
"""


def is_tuya_sharing_available() -> bool:
    """Check if tuya_sharing package is available. Always returns False."""
    return False
