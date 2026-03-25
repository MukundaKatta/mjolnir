"""Core dashboard engine for Mjolnir.

Provides metric collection, dashboard composition, and widget management
for real-time AI agent monitoring. Named after Thor's hammer -- every
metric strike lands with purpose.
"""

from __future__ import annotations

import time
import uuid
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------

class MetricType(Enum):
    """Classification of metric behaviour."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class Metric:
    """A single measurement captured at a point in time.

    Attributes:
        name:      Dot-separated metric identifier (e.g. ``agent.tokens``).
        value:     Numeric measurement.
        unit:      Human-readable unit (``"ms"``, ``"tokens"``, ``"%"``).
        timestamp: Unix epoch seconds.  Defaults to *now*.
        tags:      Arbitrary key/value annotations.
    """
    name: str
    value: float
    unit: str = ""
    timestamp: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


# ---------------------------------------------------------------------------
# MetricCollector -- accumulates a time-series per metric name
# ---------------------------------------------------------------------------

class MetricCollector:
    """Collects and stores metrics in memory.

    Supports recording individual samples, querying the latest value,
    retrieving full history, and computing simple aggregations.
    """

    def __init__(self, max_history: int = 10_000) -> None:
        self._store: Dict[str, List[Metric]] = {}
        self._max_history = max_history

    # -- recording ----------------------------------------------------------

    def record(self, metric: Metric) -> None:
        """Append *metric* to the internal time-series store."""
        series = self._store.setdefault(metric.name, [])
        series.append(metric)
        if len(series) > self._max_history:
            series[:] = series[-self._max_history:]

    def record_value(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Convenience wrapper that creates a :class:`Metric` and records it."""
        m = Metric(name=name, value=value, unit=unit, tags=tags or {})
        self.record(m)
        return m

    # -- querying -----------------------------------------------------------

    def latest(self, name: str) -> Optional[Metric]:
        """Return the most recent metric for *name*, or ``None``."""
        series = self._store.get(name)
        if not series:
            return None
        return series[-1]

    def history(self, name: str, limit: int = 0) -> List[Metric]:
        """Return recorded metrics for *name* (newest last).

        If *limit* > 0, return only the last *limit* entries.
        """
        series = self._store.get(name, [])
        if limit > 0:
            return series[-limit:]
        return list(series)

    def names(self) -> List[str]:
        """Return all known metric names."""
        return list(self._store.keys())

    def count(self, name: str) -> int:
        """Number of recorded samples for *name*."""
        return len(self._store.get(name, []))

    # -- aggregation --------------------------------------------------------

    def aggregate(
        self,
        name: str,
        func: str = "mean",
        window: int = 0,
    ) -> Optional[float]:
        """Compute a rolling aggregate over recent values.

        *func* may be ``"mean"``, ``"sum"``, ``"min"``, ``"max"``, or ``"last"``.
        *window* limits the number of recent samples (0 = all).
        """
        series = self._store.get(name, [])
        if not series:
            return None
        values = [m.value for m in (series[-window:] if window else series)]
        if func == "mean":
            return statistics.mean(values)
        if func == "sum":
            return sum(values)
        if func == "min":
            return min(values)
        if func == "max":
            return max(values)
        if func == "last":
            return values[-1]
        raise ValueError(f"Unknown aggregate function: {func}")

    def clear(self, name: Optional[str] = None) -> None:
        """Drop stored metrics.  If *name* is ``None`` drop everything."""
        if name is None:
            self._store.clear()
        else:
            self._store.pop(name, None)


# ---------------------------------------------------------------------------
# Widget -- a visual element in a dashboard
# ---------------------------------------------------------------------------

class WidgetType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    CHART = "chart"
    TABLE = "table"


@dataclass
class Widget:
    """Describes a single visual element on a dashboard.

    Attributes:
        id:            Unique widget identifier (auto-generated if empty).
        widget_type:   Visual kind -- counter, gauge, chart, or table.
        metric_source: Name of the metric this widget is bound to.
        config:        Arbitrary rendering configuration.
        title:         Human-readable label displayed in the UI.
    """
    id: str = ""
    widget_type: WidgetType = WidgetType.COUNTER
    metric_source: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    title: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"w-{uuid.uuid4().hex[:8]}"

    def render(self, collector: MetricCollector) -> Dict[str, Any]:
        """Produce a JSON-friendly snapshot of this widget's current state."""
        latest = collector.latest(self.metric_source)
        value = latest.value if latest else None
        return {
            "id": self.id,
            "type": self.widget_type.value,
            "title": self.title or self.metric_source,
            "value": value,
            "unit": latest.unit if latest else "",
            "config": self.config,
        }


# ---------------------------------------------------------------------------
# Dashboard -- an ordered collection of widgets
# ---------------------------------------------------------------------------

class Dashboard:
    """An ordered collection of :class:`Widget` instances.

    Each dashboard holds a reference to a :class:`MetricCollector` so that
    widgets can render live values.
    """

    def __init__(self, name: str, collector: MetricCollector) -> None:
        self.name = name
        self.collector = collector
        self._widgets: List[Widget] = []
        self.created_at: float = time.time()

    def add_widget(self, widget: Widget) -> None:
        self._widgets.append(widget)

    def remove_widget(self, widget_id: str) -> bool:
        before = len(self._widgets)
        self._widgets = [w for w in self._widgets if w.id != widget_id]
        return len(self._widgets) < before

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        for w in self._widgets:
            if w.id == widget_id:
                return w
        return None

    @property
    def widgets(self) -> List[Widget]:
        return list(self._widgets)

    def snapshot(self) -> Dict[str, Any]:
        """Render every widget and return a dashboard-level snapshot."""
        return {
            "dashboard": self.name,
            "widgets": [w.render(self.collector) for w in self._widgets],
            "widget_count": len(self._widgets),
        }


# ---------------------------------------------------------------------------
# DashboardBuilder -- fluent API for constructing dashboards
# ---------------------------------------------------------------------------

class DashboardBuilder:
    """Fluent builder for assembling a :class:`Dashboard`.

    Example::

        dashboard = (
            DashboardBuilder("ops", collector)
            .add_counter("req_total", title="Requests")
            .add_gauge("cpu", title="CPU %")
            .add_chart("latency", title="Latency (ms)")
            .add_table("errors", title="Recent Errors")
            .build()
        )
    """

    def __init__(self, name: str, collector: MetricCollector) -> None:
        self._name = name
        self._collector = collector
        self._widgets: List[Widget] = []

    # -- fluent helpers -----------------------------------------------------

    def add_counter(self, metric_source: str, title: str = "", **cfg: Any) -> "DashboardBuilder":
        self._widgets.append(Widget(
            widget_type=WidgetType.COUNTER,
            metric_source=metric_source,
            title=title,
            config=cfg,
        ))
        return self

    def add_gauge(self, metric_source: str, title: str = "", **cfg: Any) -> "DashboardBuilder":
        self._widgets.append(Widget(
            widget_type=WidgetType.GAUGE,
            metric_source=metric_source,
            title=title,
            config=cfg,
        ))
        return self

    def add_chart(self, metric_source: str, title: str = "", **cfg: Any) -> "DashboardBuilder":
        self._widgets.append(Widget(
            widget_type=WidgetType.CHART,
            metric_source=metric_source,
            title=title,
            config=cfg,
        ))
        return self

    def add_table(self, metric_source: str, title: str = "", **cfg: Any) -> "DashboardBuilder":
        self._widgets.append(Widget(
            widget_type=WidgetType.TABLE,
            metric_source=metric_source,
            title=title,
            config=cfg,
        ))
        return self

    def build(self) -> Dashboard:
        """Construct the :class:`Dashboard` and return it."""
        dash = Dashboard(self._name, self._collector)
        for w in self._widgets:
            dash.add_widget(w)
        return dash


# ---------------------------------------------------------------------------
# DashboardEngine -- top-level orchestrator
# ---------------------------------------------------------------------------

class DashboardEngine:
    """Top-level orchestrator that owns collectors and dashboards.

    Provides a single entry-point for the rest of the application to
    create dashboards, record metrics, and retrieve snapshots.
    """

    def __init__(self) -> None:
        self.collector = MetricCollector()
        self._dashboards: Dict[str, Dashboard] = {}
        self._hooks: List[Callable[[Metric], None]] = []

    # -- dashboard management -----------------------------------------------

    def create_dashboard(self, name: str) -> Dashboard:
        dash = Dashboard(name, self.collector)
        self._dashboards[name] = dash
        return dash

    def get_dashboard(self, name: str) -> Optional[Dashboard]:
        return self._dashboards.get(name)

    def list_dashboards(self) -> List[str]:
        return list(self._dashboards.keys())

    def remove_dashboard(self, name: str) -> bool:
        return self._dashboards.pop(name, None) is not None

    # -- metric recording ---------------------------------------------------

    def record(self, metric: Metric) -> None:
        """Record a metric and fire any registered hooks."""
        self.collector.record(metric)
        for hook in self._hooks:
            hook(metric)

    def record_value(self, name: str, value: float, unit: str = "", tags: Optional[Dict[str, str]] = None) -> Metric:
        m = self.collector.record_value(name, value, unit, tags)
        for hook in self._hooks:
            hook(m)
        return m

    def on_metric(self, hook: Callable[[Metric], None]) -> None:
        """Register a callback invoked on every recorded metric."""
        self._hooks.append(hook)

    # -- snapshot -----------------------------------------------------------

    def snapshot(self, dashboard_name: Optional[str] = None) -> Dict[str, Any]:
        """Return a JSON-friendly snapshot of one or all dashboards."""
        if dashboard_name:
            dash = self._dashboards.get(dashboard_name)
            if dash is None:
                return {"error": f"Dashboard '{dashboard_name}' not found"}
            return dash.snapshot()
        return {
            "dashboards": {
                name: dash.snapshot() for name, dash in self._dashboards.items()
            }
        }

    def builder(self, name: str) -> DashboardBuilder:
        """Return a :class:`DashboardBuilder` pre-wired to this engine's collector."""
        return DashboardBuilder(name, self.collector)
