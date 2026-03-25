"""Tests for mjolnir.alerts -- rules, history, and alert manager."""

from mjolnir.alerts import (
    Alert,
    AlertHistory,
    AlertManager,
    AlertRule,
    Condition,
    Severity,
)
from mjolnir.core import MetricCollector


class TestAlertRule:
    def test_gt(self):
        r = AlertRule(metric="cpu", condition=Condition.GT, threshold=80)
        assert r.evaluate(90) is True
        assert r.evaluate(80) is False

    def test_lt(self):
        r = AlertRule(metric="mem", condition=Condition.LT, threshold=10)
        assert r.evaluate(5) is True
        assert r.evaluate(15) is False

    def test_eq(self):
        r = AlertRule(metric="x", condition=Condition.EQ, threshold=42)
        assert r.evaluate(42) is True
        assert r.evaluate(43) is False

    def test_gte_lte(self):
        gte = AlertRule(metric="x", condition=Condition.GTE, threshold=10)
        assert gte.evaluate(10) is True
        assert gte.evaluate(9) is False
        lte = AlertRule(metric="x", condition=Condition.LTE, threshold=10)
        assert lte.evaluate(10) is True
        assert lte.evaluate(11) is False

    def test_auto_id(self):
        r = AlertRule(metric="m", condition=Condition.GT, threshold=0)
        assert r.rule_id.startswith("rule-")


class TestAlertHistory:
    def test_add_and_count(self):
        h = AlertHistory()
        h.add(Alert(rule_id="r1", metric_name="cpu", metric_value=95,
                     severity=Severity.CRITICAL, message="hot"))
        assert h.count == 1

    def test_by_severity(self):
        h = AlertHistory()
        h.add(Alert(rule_id="r1", metric_name="a", metric_value=1,
                     severity=Severity.INFO, message=""))
        h.add(Alert(rule_id="r2", metric_name="b", metric_value=2,
                     severity=Severity.CRITICAL, message=""))
        assert len(h.by_severity(Severity.CRITICAL)) == 1

    def test_by_metric(self):
        h = AlertHistory()
        h.add(Alert(rule_id="r1", metric_name="cpu", metric_value=1,
                     severity=Severity.INFO, message=""))
        assert len(h.by_metric("cpu")) == 1
        assert len(h.by_metric("mem")) == 0

    def test_clear(self):
        h = AlertHistory()
        h.add(Alert(rule_id="r1", metric_name="x", metric_value=0,
                     severity=Severity.INFO, message=""))
        h.clear()
        assert h.count == 0


class TestAlertManager:
    def test_check_fires_alert(self):
        c = MetricCollector()
        c.record_value("cpu", 95)
        mgr = AlertManager(c)
        mgr.add_rule(AlertRule(metric="cpu", condition=Condition.GT,
                                threshold=80, severity=Severity.CRITICAL))
        fired = mgr.check()
        assert len(fired) == 1
        assert fired[0].severity == Severity.CRITICAL

    def test_check_no_fire(self):
        c = MetricCollector()
        c.record_value("cpu", 50)
        mgr = AlertManager(c)
        mgr.add_rule(AlertRule(metric="cpu", condition=Condition.GT, threshold=80))
        assert mgr.check() == []

    def test_callback(self):
        captured = []
        c = MetricCollector()
        c.record_value("x", 100)
        mgr = AlertManager(c)
        mgr.on_alert(lambda a: captured.append(a))
        mgr.add_rule(AlertRule(metric="x", condition=Condition.GT, threshold=0))
        mgr.check()
        assert len(captured) == 1

    def test_remove_rule(self):
        c = MetricCollector()
        mgr = AlertManager(c)
        rule = AlertRule(metric="m", condition=Condition.GT, threshold=0)
        mgr.add_rule(rule)
        assert mgr.remove_rule(rule.rule_id) is True
        assert mgr.list_rules() == []

    def test_history_persists(self):
        c = MetricCollector()
        c.record_value("cpu", 99)
        mgr = AlertManager(c)
        mgr.add_rule(AlertRule(metric="cpu", condition=Condition.GT, threshold=50))
        mgr.check()
        assert mgr.history.count == 1
