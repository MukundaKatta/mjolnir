# Architecture

Mjolnir is organised into three focused modules with no external dependencies.

## Module overview

```
┌─────────────────────────────────────────────┐
│                 DashboardEngine              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Collector  │  │Dashboard │  │  Hooks   │ │
│  │  (metrics)  │──│(widgets) │  │(callbacks│ │
│  └────────────┘  └──────────┘  └──────────┘ │
└──────────┬──────────────────────────┬────────┘
           │                          │
     ┌─────▼─────┐            ┌──────▼───────┐
     │AlertManager│            │SessionTracker│
     │  (rules)   │            │  (agents)    │
     └───────────┘            └──────────────┘
```

### core.py

Central module. `MetricCollector` stores time-series data keyed by metric name. `Dashboard` holds an ordered list of `Widget` instances, each bound to a metric source. `DashboardBuilder` provides a fluent API. `DashboardEngine` ties everything together with hooks for cross-cutting concerns.

### agents.py

`AgentMonitor` tracks a single AI agent session -- status, context usage, tool calls, and to-do progress. `AgentSnapshot` is an immutable freeze of that state. `SessionTracker` manages the full set of monitored agents.

### alerts.py

`AlertRule` declares a threshold condition. `AlertManager` evaluates rules against the collector and fires `Alert` instances into `AlertHistory`. Callbacks allow external systems to react in real time.

### config.py

`MjolnirConfig` reads environment variables prefixed with `MJOLNIR_` and falls back to sensible defaults.

## Data flow

1. External code records metrics via `DashboardEngine.record_value()`.
2. Hooks (including `AlertManager.check()`) react to new data.
3. Dashboards render widget snapshots from the collector.
4. Agent monitors produce snapshots independently of the metric pipeline.

## Design decisions

- **Zero dependencies** -- the library relies only on the Python 3.9+ standard library.
- **In-memory storage** -- keeps the architecture simple; persistence can be layered on later.
- **Fluent builder** -- dashboards are built declaratively, reducing boilerplate.
