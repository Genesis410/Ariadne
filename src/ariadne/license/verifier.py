"""Offline Ed25519 license token verifier."""

import base64
import json
import os
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Built-in public keys for offline verification
BUILTIN_PUBLIC_KEYS: Dict[str, bytes] = {
    "key_2026_01": bytes.fromhex(
        "7d38392576b4a530f2c0022415174542d8ca2c4cbb8f4070a2a466fcad15024b"
    )
}

FREE_TIER_SEED_LIMIT = 1000


class LicenseInfo:
    def __init__(self, is_pro: bool, licensee: str = "Community (Free)", limit: Optional[int] = FREE_TIER_SEED_LIMIT):
        self.is_pro = is_pro
        self.licensee = licensee
        self.seed_limit = limit

    @property
    def can_run_unlimited(self) -> bool:
        return self.is_pro or self.seed_limit is None


def verify_license_token(token_str: str) -> Tuple[bool, str, Optional[int]]:
    """
    Verify Ed25519 offline license token.
    Returns: (is_valid_pro, licensee_name, seed_limit)
    """
    try:
        raw_bytes = base64.b64decode(token_str)
        token_data = json.loads(raw_bytes.decode("utf-8"))
        payload = token_data["payload"]
        sig_bytes = bytes.fromhex(token_data["signature"])
        kid = payload.get("kid", "key_2026_01")

        if kid not in BUILTIN_PUBLIC_KEYS:
            return False, "Unknown key ID in license", FREE_TIER_SEED_LIMIT

        pub_key = Ed25519PublicKey.from_public_bytes(BUILTIN_PUBLIC_KEYS[kid])
        message = json.dumps(payload, sort_keys=True).encode("utf-8")
        pub_key.verify(sig_bytes, message)

        licensee = payload.get("licensee", "Pro Licensee")
        tier = payload.get("tier", "pro")
        if tier == "pro":
            return True, licensee, None
        return False, licensee, FREE_TIER_SEED_LIMIT
    except Exception:
        return False, "Invalid license key", FREE_TIER_SEED_LIMIT


def get_active_license() -> LicenseInfo:
    """Read license from ARIADNE_LICENSE_KEY env or local .ariadne/license.key."""
    token = os.environ.get("ARIADNE_LICENSE_KEY", "").strip()
    if not token and os.path.exists(".ariadne/license.key"):
        try:
            with open(".ariadne/license.key", "r", encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            token = ""

    if not token:
        return LicenseInfo(is_pro=False, licensee="Community Free Tier", limit=FREE_TIER_SEED_LIMIT)

    is_pro, name, limit = verify_license_token(token)
    return LicenseInfo(is_pro=is_pro, licensee=name, limit=limit)
