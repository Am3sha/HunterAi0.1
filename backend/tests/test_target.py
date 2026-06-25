"""Tests for the Target entity and domain normalization."""

from __future__ import annotations

import pytest

from app.domain.entities.target import Target, normalize_domain


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Example.com", "example.com"),
        ("https://www.example.com/path?q=1", "www.example.com"),
        ("http://api.example.com:8443", "api.example.com"),
        ("  sub.example.co.uk.  ", "sub.example.co.uk"),
    ],
)
def test_normalize_domain(raw: str, expected: str) -> None:
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a domain", "localhost", "http://", "exam ple.com"])
def test_normalize_domain_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_domain(raw)


def test_target_create_assigns_id_and_normalizes() -> None:
    target = Target.create("HTTPS://WWW.Example.com/")
    assert target.domain == "www.example.com"
    assert target.id is not None
    assert target.created_at is not None
