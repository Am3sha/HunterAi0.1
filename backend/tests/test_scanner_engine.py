"""Tests for the ScannerEngine orchestration (with fake plugins)."""

from __future__ import annotations

from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.domain.entities.finding import Finding, Severity
from app.domain.entities.scanner import (
    PluginMetadata,
    PluginRunStatus,
    ScanContext,
)


class _FakePlugin:
    """Minimal ScannerPlugin implementation for tests."""

    def __init__(self, name: str, findings: list[Finding] | None = None, boom: bool = False):
        self.metadata = PluginMetadata(name=name, title=name)
        self._findings = findings or []
        self._boom = boom

    def scan(self, context: ScanContext) -> list[Finding]:
        if self._boom:
            raise RuntimeError(f"{self.metadata.name} exploded")
        return self._findings


def _finding(plugin: str, severity: Severity = Severity.LOW) -> Finding:
    return Finding(plugin=plugin, name="x", severity=severity, target="https://example.com")


def _context() -> ScanContext:
    return ScanContext(target_domain="example.com")


def test_engine_aggregates_findings_from_all_plugins() -> None:
    engine = ScannerEngine(
        [
            _FakePlugin("a", [_finding("a", Severity.HIGH)]),
            _FakePlugin("b", [_finding("b"), _finding("b")]),
        ]
    )
    result = engine.run(_context())
    assert result.total_findings == 3
    assert all(e.status is PluginRunStatus.OK for e in result.executions)
    assert {e.plugin for e in result.executions} == {"a", "b"}


def test_engine_isolates_plugin_failure() -> None:
    engine = ScannerEngine(
        [
            _FakePlugin("ok", [_finding("ok")]),
            _FakePlugin("bad", boom=True),
            _FakePlugin("ok2", [_finding("ok2")]),
        ]
    )
    result = engine.run(_context())
    # A failing plugin does not abort the others.
    assert result.total_findings == 2
    assert result.failed_plugins == ["bad"]
    failed = next(e for e in result.executions if e.plugin == "bad")
    assert failed.status is PluginRunStatus.FAILED
    assert failed.error is not None and "exploded" in failed.error


def test_engine_records_execution_counts_and_duration() -> None:
    ticks = iter([1.0, 1.5])  # start, end
    engine = ScannerEngine([_FakePlugin("a", [_finding("a")])], timer=lambda: next(ticks))
    result = engine.run(_context())
    execution = result.executions[0]
    assert execution.findings == 1
    assert execution.duration_seconds == 0.5


def test_engine_with_no_plugins_returns_empty() -> None:
    result = ScannerEngine([]).run(_context())
    assert result.total_findings == 0
    assert result.executions == ()


def test_result_counts_by_severity_and_sorting() -> None:
    engine = ScannerEngine(
        [
            _FakePlugin(
                "a",
                [_finding("a", Severity.LOW), _finding("a", Severity.CRITICAL)],
            )
        ]
    )
    result = engine.run(_context())
    assert result.counts_by_severity["critical"] == 1
    assert result.counts_by_severity["low"] == 1
    assert [f.severity for f in result.sorted_findings()] == [Severity.CRITICAL, Severity.LOW]
