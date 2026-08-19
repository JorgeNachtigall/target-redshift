"""Identifier helpers for Redshift.

Kept dependency-free so the naming rules can be unit tested without a database
or the rest of the target's runtime dependencies.
"""

from __future__ import annotations

import hashlib

# Redshift truncates identifiers longer than this silently, on both CREATE and
# ALTER. That breaks schema reconciliation: the target compares its full-length
# property names against the truncated names Redshift stored, never matches, and
# re-issues ALTER TABLE ADD COLUMN forever (Redshift then raises 42701
# "column already exists"). Normalising up front keeps both sides in agreement.
REDSHIFT_MAX_IDENTIFIER_BYTES = 127

# Bytes reserved for the "_" separator plus the 8-char disambiguating digest.
_DIGEST_SUFFIX_BYTES = 9


def truncate_identifier(name: str, limit: int = REDSHIFT_MAX_IDENTIFIER_BYTES) -> str:
    """Shorten an identifier to Redshift's limit, keeping it unique and stable.

    Names within the limit are returned unchanged. Longer names are cut and given a
    short digest of the *original* name, so that two names sharing a long common
    prefix do not collapse into the same column.

    Args:
        name: The identifier to shorten.
        limit: Maximum identifier length in bytes.

    Returns:
        An identifier of at most ``limit`` bytes, deterministic for a given input.
    """
    encoded = name.encode("utf-8")
    if len(encoded) <= limit:
        return name

    digest = hashlib.md5(encoded, usedforsecurity=False).hexdigest()[:8]
    # Decode with errors="ignore" in case the cut lands mid multi-byte character.
    stem = encoded[: limit - _DIGEST_SUFFIX_BYTES].decode("utf-8", errors="ignore")
    return f"{stem}_{digest}"
