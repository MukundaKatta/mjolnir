"""Tests for mjolnir.core -- metrics, widgets, dashboards, and engine."""

import time
import pytest
from mjolnir.core import (
    Metric,
    MetricCollector,
    MetricType,
    Widget,
    WidgetType,
    Dashboard,
    DashboardBuilder,
    DashboardEngine,
)


# -- Metric -----------------------------------------------------------------

class TestMetric:
    def test_default_timestamp(self):
        m = Metric(name="cpu", value=42.0)
        assert m.timestamp > 0

    def test_explicit_fields(self):
        m = Metric(name="mem", value=1024, unit="MB", timestamp=1.0, tags={"host": "a"})
        assert m.name == "mem"
        assert m.value == 1024
        assert m.unit == "MB"
        assert m.timestamp == 1.0
        assert m.tags == {"host": "a"}


# -- MetricCollector --------------------------------------------------------

class TestMetricCollector:
    def test_record_and_latest(self):
        c = MetricCollector()
        c.record(Metric(name="x", value=10))
        c.record(Metric(name="x", value=20))
        assert c.latest("x").value == 20

    def test_latest_missing(self):
        c = MetricCollector()
        assert c.latest("nope") is None

    def test_history_limit(self):
        c = MetricCollector()
        for i in range(5):
            c.record_value("h", float(i))
        assert len(c.history("h", limit=3)) == 3

    def test_names(self):
        c = MetricCollector()
        c.record_value("a", 1)
        c.record_value("b", 2)
        assert set(c.names()) == {"a", "b"}

    def test_count(self):
        c = MetricCollector()
        c.record_value("c", 1)
        c.record_value("c", 2)
        assert c.count("c") == 2

    def test_aggregate_mean(self):
        c = MetricCollector()
        for v in [10, 20, 30]:
            c.record_value("s", float(v))
        assert c.aggregate("s", "mean") == 20.0

    def test_aggregate_sum(self):
        c = MetricCollector()
        for v in [1, 2, 3]:
            c.record_value("s", float(v))
        assert c.aggregate("s", "sum") == 6.0

    def test_aggregate_min_max(self):
        c = MetricCollector()
        for v in [5, 3, 9]:
            c.record_value("s", float(v))
        assert c.aggregate("s", "min") == 3.0
        assert c.aggregate("s", "max") == 9.0

    def test_aggregate_window(self):
        c = MetricCollector()
        for v in [100, 1, 2, 3]:
            c.record_value("s", float(v))
        assert c.aggregate("s", "mean", window=3) == 2.0

    def test_aggregate_unknown_func(self):
        c = MetricCollector()
        c.record_value("s", 1)
        with pytest.raises(ValueError):
            c.aggregate("s", "median")

    def test_aggregate_empty(self):
        c = MetricCollector()
        assert c.aggregate("missing") is None

    def test_clear_specific(self):
        c = MetricCollector()
        c.record_value("a", 1)
        c.record_value("b", 2)
        c.clear("a")
        assert c.latest("a") is None
        assert c.latest("b") is not None

    def test_clear_all(self):
        c = MetricCollector()
        c.record_value("a", 1)
        c.clear()
        assert c.names() == []

    def test_max_history_cap(self):
        c = MetricCollector(max_history=5)
        for i in range(10):
            c.record_value("x", float(i))
        assert c.count("x") == 5
        assert c.history("x")[0].value == 5.0


# -- Widget -----------------------------------------------------------------

class TestWidget:
    def test_auto_id(self):
        w = Widget()
        assert w.id.startswith("w-")

    def test_render(self):
        c = MetricCollector()
        c.record_value("cpu", 75.0, unit="%")
        w = Widget(widget_type=WidgetType.GAUGE, metric_source="cpu", title="CPU")
        rendered = w.render(c)
        assert rendered["value"] == 75.0
        assert rendered["type"] == "gauge"

    def test_render_missing_metric(self):
        c = MetricCollector()
        w = Widget(metric_source="missing")
        rendered = w.render(c)
        assert rendered["value"] is None


# -- Dashboard --------------------------------------------------------------

class TestDashboard:
    def test_add_remove_widget(self):
        c = MetricCollector()
        d = Dashboard("test", c)
        w = Widget(id="w1")
        d.add_widget(w)
        assert len(d.widgets) == 1
        assert d.get_widget("w1") is w
        assert d.remove_widget("w1") is True
        assert len(d.widgets) == 0

    def test_snapshot(self):
        c = MetricCollector()
        c.record_value("m", 5)
        d = Dashboard("snap", c)
        d.add_widget(Widget(metric_source="m"))
        snap = d.snapshot()
        assert snap["dashboard"] == "snap"
        assert snap["widget_count"] == 1


# -- DashboardBuilder ------------------------------------------------------

class TestDashboardBuilder:
    def test_fluent_build(self):
        c = MetricCollector()
        dash = (
            DashboardBuilder("ops", c)
            .add_counter("requests", title="Reqs")
            .add_gauge("cpu", title="CPU")
            .add_chart("latency", title="Latency")
            .add_table("errors", title="Errors")
            .build()
        )
        assert dash.name == "ops"
        assert len(dash.widgets) == 4
        types = [w.widget_type for w in dash.widgets]
        assert types == [
            WidgetType.COUNTER,
            WidgetType.GAUGE,
            WidgetType.CHART,
            WidgetType.TABLE,
        ]


# -- DashboardEngine -------------------------------------------------------

class TestDashboardEngine:
    def test_create_and_list(self):
        e = DashboardEngine()
        e.create_dashboard("d1")
        assert "d1" in e.list_dashboards()

    def test_remove_dashboard(self):
        e = DashboardEngine()
        e.create_dashboard("d1")
        assert e.remove_dashboard("d1") is True
        assert e.remove_dashboard("d1") is False

    def test_record_and_snapshot(self):
        e = DashboardEngine()
        d = e.create_dashboard("main")
        d.add_widget(Widget(metric_source="cpu"))
        e.record_value("cpu", 88.0, "%")
        snap = e.snapshot("main")
        assert snap["widgets"][0]["value"] == 88.0

    def test_on_metric_hook(self):
        captured = []
        e = DashboardEngine()
        e.on_metric(lambda m: captured.append(m))
        e.record_value("x", 1)
        assert len(captured) == 1

    def test_snapshot_missing_dashboard(self):
        e = DashboardEngine()
        snap = e.snapshot("nope")
        assert "error" in snap

    def test_builder_helper(self):
        e = DashboardEngine()
        b = e.builder("b")
        dash = b.add_counter("c").build()
        assert dash.name == "b"
