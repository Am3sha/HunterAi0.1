"""Tests for the advanced Finding model (Sprint 2 M2.1, domain layer)."""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.scanner import PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin


def test_finding_advanced_fields_default_to_empty() -> None:
    f = Finding(plugin="p", name="n", severity=Severity.LOW, target="https://example.com")
    assert f.cvss is None
    assert f.cwe_ids == ()
    assert f.owasp_categories == ()
    assert f.remediation is None
    # Existing fields unchanged.
    assert f.confidence is Confidence.MEDIUM
    assert f.references == ()
    assert f.metadata == {}


def test_finding_accepts_advanced_fields() -> None:
    cvss = Cvss(version="3.1", vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N", base_score=7.5)
    f = Finding(
        plugin="p",
        name="n",
        severity=Severity.HIGH,
        target="https://example.com",
        cvss=cvss,
        cwe_ids=("CWE-79", "CWE-80"),
        owasp_categories=("A03:2021-Injection",),
        remediation="Encode output.",
    )
    assert f.cvss == cvss
    assert f.cvss.base_score == 7.5
    assert f.cwe_ids == ("CWE-79", "CWE-80")
    assert f.owasp_categories == ("A03:2021-Injection",)
    assert f.remediation == "Encode output."


def test_cvss_is_immutable() -> None:
    cvss = Cvss(version="3.1", vector="CVSS:3.1/...", base_score=5.0)
    try:
        cvss.base_score = 9.0  # type: ignore[misc]
    except AttributeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Cvss should be frozen/immutable")


class _RichPlugin(BaseScannerPlugin):
    metadata = PluginMetadata(name="rich", title="Rich")

    def scan(self, context: ScanContext) -> list[Finding]:
        return []


def test_build_finding_supports_advanced_fields() -> None:
    plugin = _RichPlugin()
    cvss = Cvss(version="3.1", vector="CVSS:3.1/AV:N", base_score=6.1)
    finding = plugin.build_finding(
        name="Reflected XSS",
        severity=Severity.HIGH,
        target="https://example.com/s?q=1",
        cvss=cvss,
        cwe_ids=["CWE-79"],
        owasp_categories=["A03:2021-Injection"],
        remediation="Contextually encode user input.",
    )
    assert finding.plugin == "rich"
    assert finding.cvss == cvss
    assert finding.cwe_ids == ("CWE-79",)
    assert finding.owasp_categories == ("A03:2021-Injection",)
    assert finding.remediation == "Contextually encode user input."


def test_build_finding_defaults_remain_backward_compatible() -> None:
    plugin = _RichPlugin()
    finding = plugin.build_finding(
        name="Missing header", severity=Severity.LOW, target="https://example.com"
    )
    assert finding.cvss is None
    assert finding.cwe_ids == ()
    assert finding.owasp_categories == ()
    assert finding.remediation is None
