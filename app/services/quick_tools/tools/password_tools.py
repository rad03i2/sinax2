# -*- coding: utf-8 -*-
"""
SINAX Password & Security Utilities
Cryptographically secure password, passphrase, token, and UUID generation,
plus local offline password strength and entropy estimation.
"""

import math
import os
import secrets
import string
from typing import Any, Dict, List, Optional, Tuple
import uuid


PASSPHRASE_WORDS = [
    "amber", "anchor", "apple", "apron", "arch", "arrow", "atlas", "autumn",
    "baker", "banner", "basin", "beacon", "berry", "birch", "blaze", "bloom",
    "breeze", "bridge", "cabin", "canyon", "castle", "cedar", "charm", "cliff",
    "cloud", "clover", "comet", "coral", "crane", "creek", "crown", "crystal",
    "dawn", "delta", "desert", "dragon", "drift", "eagle", "echo", "ember",
    "falcon", "feather", "field", "flame", "flint", "forest", "fountain", "fox",
    "frost", "galaxy", "garden", "glacier", "globe", "grove", "harbor", "haven",
    "hawk", "horizon", "island", "jasper", "jungle", "lagoon", "lantern", "leaf",
    "meadow", "meteor", "moon", "moss", "mountain", "nebula", "nest", "north",
    "oasis", "ocean", "orbit", "otter", "palm", "path", "pearl", "pebble",
    "phoenix", "pine", "planet", "pond", "prairie", "quartz", "quiver", "radiant",
    "rain", "raven", "reef", "ridge", "river", "robin", "sail", "shadow",
    "silver", "sky", "solar", "spark", "spruce", "star", "storm", "stream",
    "summit", "sunset", "thunder", "tide", "timber", "trail", "valley", "wave"
]


class PasswordTools:
    """Offline cryptographic random generation and security analysis."""

    @staticmethod
    def generate_password(
        length: int = 16,
        use_upper: bool = True,
        use_lower: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
        exclude_ambiguous: bool = True
    ) -> str:
        """Generates a cryptographically strong password using secrets module."""
        length = max(4, min(length, 256))
        pool = ""
        required_chars = []

        ambiguous = "l1IO0|`'\"~,;:<>.^/\\" if exclude_ambiguous else ""

        if use_lower:
            chars = "".join(c for c in string.ascii_lowercase if c not in ambiguous)
            pool += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        if use_upper:
            chars = "".join(c for c in string.ascii_uppercase if c not in ambiguous)
            pool += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        if use_digits:
            chars = "".join(c for c in string.digits if c not in ambiguous)
            pool += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        if use_symbols:
            special_safe = "!@#$%&*-_=+"
            chars = "".join(c for c in special_safe if c not in ambiguous)
            pool += chars
            if chars:
                required_chars.append(secrets.choice(chars))

        if not pool:
            pool = string.ascii_letters + string.digits

        remaining_length = length - len(required_chars)
        random_chars = [secrets.choice(pool) for _ in range(max(0, remaining_length))]
        all_chars = required_chars + random_chars

        # Cryptographic shuffle
        result = []
        while all_chars:
            idx = secrets.randbelow(len(all_chars))
            result.append(all_chars.pop(idx))

        return "".join(result)

    @staticmethod
    def generate_passphrase(word_count: int = 4, separator: str = "-") -> str:
        """Generates a memorable multi-word passphrase from internal wordlist."""
        word_count = max(2, min(word_count, 12))
        chosen = [secrets.choice(PASSPHRASE_WORDS) for _ in range(word_count)]
        return separator.join(chosen)

    @staticmethod
    def estimate_password_strength(password: str) -> Dict[str, Any]:
        """
        Estimates password entropy, complexity, and weakness metrics.
        Executed 100% locally with zero external network queries.
        """
        if not password:
            return {
                "score": 0,
                "label_ar": "فارغة",
                "entropy_bits": 0.0,
                "length": 0,
                "recommendations": ["أدخل كلمة مرور لفحص قوتها."],
            }

        length = len(password)
        pool_size = 0
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(not c.isalnum() for c in password)

        if has_lower:
            pool_size += 26
        if has_upper:
            pool_size += 26
        if has_digit:
            pool_size += 10
        if has_symbol:
            pool_size += 32

        pool_size = max(pool_size, 10)
        entropy = length * math.log2(pool_size)

        recommendations = []
        if length < 12:
            recommendations.append("زيادة الطول إلى 14 حرفاً على الأقل يرفع الأمان أضعافاً.")
        if not (has_lower and has_upper):
            recommendations.append("اخلط بين الأحرف الكبيرة والصغيرة.")
        if not has_digit:
            recommendations.append("أضف أرقاماً عشوائية.")
        if not has_symbol:
            recommendations.append("أضف رموزاً خاصة مثل (@, #, $, %).")

        if entropy < 36:
            score = 1
            label = "ضعيفة جداً"
        elif entropy < 55:
            score = 2
            label = "ضعيفة"
        elif entropy < 70:
            score = 3
            label = "متوسطة"
        elif entropy < 90:
            score = 4
            label = "قوية"
        else:
            score = 5
            label = "قوية جداً وممتازة"

        return {
            "score": score,
            "label_ar": label,
            "entropy_bits": round(entropy, 1),
            "length": length,
            "has_lower": has_lower,
            "has_upper": has_upper,
            "has_digit": has_digit,
            "has_symbol": has_symbol,
            "recommendations": recommendations or ["كلمة المرور ممتازة وتفي بالمعايير الأمنية."],
        }

    @staticmethod
    def generate_uuid(version: int = 4, batch_count: int = 1) -> List[str]:
        """Generates single or batch UUIDs."""
        count = max(1, min(batch_count, 5000))
        results = []
        for _ in range(count):
            if version == 1:
                results.append(str(uuid.uuid1()))
            else:
                results.append(str(uuid.uuid4()))
        return results

    @staticmethod
    def generate_secure_token(num_bytes: int = 32, encoding: str = "hex") -> str:
        """Generates cryptographically secure random token."""
        raw = secrets.token_bytes(num_bytes)
        if encoding == "base64":
            import base64
            return base64.b64encode(raw).decode("ascii")
        return raw.hex()

    @staticmethod
    def format_totp_uri(secret: str, account_label: str = "SINAX User", issuer: str = "SINAX") -> str:
        """Formats otpauth URI for TOTP authenticators without persisting secret."""
        clean_secret = secret.replace(" ", "").upper()
        from urllib.parse import quote
        return f"otpauth://totp/{quote(issuer)}:{quote(account_label)}?secret={clean_secret}&issuer={quote(issuer)}"
