"""Unit tests for Redshift identifier length handling."""

from __future__ import annotations

import pytest

from target_redshift.identifiers import (
    REDSHIFT_MAX_IDENTIFIER_BYTES as LIMIT,
)
from target_redshift.identifiers import (
    truncate_identifier,
)

# The header that first surfaced this, from a survey sheet. Redshift stored it
# truncated at 127 bytes, so the target kept re-adding it and failing with 42701.
LONG_SURVEY_HEADER = (
    "i_understand_that_i_may_only_claim_hours_once_for_each_course_in_my_states_"
    "reporting_period_and_any_duplicate_certificates_will_not_be_honored"
)


@pytest.mark.parametrize("name", ["id", "created_at", "a" * (LIMIT - 1), "a" * LIMIT])
def test_names_within_limit_are_untouched(name: str) -> None:
    """Names at or under the limit must pass through unchanged."""
    assert truncate_identifier(name) == name


def test_over_limit_is_shortened_to_the_limit() -> None:
    """An over-long name is cut to exactly the limit, so Redshift stores it verbatim."""
    result = truncate_identifier("a" * (LIMIT + 1))
    assert len(result.encode("utf-8")) == LIMIT


def test_real_world_header_fits() -> None:
    """The survey header that triggered the 42701 loop now fits."""
    assert len(LONG_SURVEY_HEADER) > LIMIT
    assert len(truncate_identifier(LONG_SURVEY_HEADER).encode("utf-8")) == LIMIT


def test_is_deterministic() -> None:
    """Re-running must produce the same column name, or every run re-adds it."""
    assert truncate_identifier(LONG_SURVEY_HEADER) == truncate_identifier(LONG_SURVEY_HEADER)


def test_shared_long_prefix_does_not_collide() -> None:
    """Two distinct questions sharing 127+ characters must stay distinct columns."""
    shared = "q" * LIMIT
    assert truncate_identifier(shared + "_option_a") != truncate_identifier(shared + "_option_b")


def test_result_is_prefixed_by_the_original() -> None:
    """Truncated names stay recognisable, so they can be traced back to the source."""
    result = truncate_identifier(LONG_SURVEY_HEADER)
    assert LONG_SURVEY_HEADER.startswith(result.rsplit("_", 1)[0])


def test_multibyte_characters_are_not_split() -> None:
    """A cut landing mid-character must not produce invalid UTF-8."""
    result = truncate_identifier("é" * LIMIT)
    assert len(result.encode("utf-8")) <= LIMIT
    result.encode("utf-8").decode("utf-8")  # raises if malformed
