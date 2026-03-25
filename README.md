# Mjolnir

**Real-time dashboard for AI coding agents** -- metrics collection, agent monitoring, and threshold-based alerts.

Named after Thor's legendary hammer, Mjolnir strikes with precision: every metric is captured, every agent is watched, and every threshold breach triggers an alert.

[![CI](https://github.com/MukundaKatta/mjolnir/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/mjolnir/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/Live_Demo-Visit_Site-blue?style=for-the-badge)](https://MukundaKatta.github.io/mjolnir/)
[![License](https://img.shields.io/github/license/MukundaKatta/mjolnir?style=flat-square)](LICENSE)

## Features

- **Metric Collection** -- record counters, gauges, and histograms with tags and timestamps.
- **Dashboard Engine** -- compose dashboards from widgets using a fluent builder API.
- **Agent Monitoring** -- track agent status, context window usage, tool invocations, and to-do progress.
- **Threshold Alerts** -- define rules (gt / lt / eq / gte / lte) with severity levels and callbacks.

## Quick start

```bash
# Clone and run tests (zero external dependencies)
git clone https://github.com/MukundaKatta/mjolnir.git
cd mjolnir
PYTHONPATH=src python3 -m pytest tests/ -v --tb=short
```

## Project layout

```
src/mjolnir/
  core.py      Dashboard engine, metrics, widgets, builder
  agents.py    Agent monitor, snapshots, session tracker
  alerts.py    Alert rules, history, alert manager
  config.py    Environment-based configuration
  cli.py       Command-line interface
```

## Usage

```python
from mjolnir.core import DashboardEngine
from mjolnir.agents import SessionTracker, AgentStatus
from mjolnir.alerts import AlertManager, AlertRule, Condition, Severity

# Create engine and record metrics
engine = DashboardEngine()
engine.record_value("cpu", 72.5, "%")

# Build a dashboard
dash = (
    engine.builder("ops")
    .add_gauge("cpu", title="CPU Usage")
    .add_counter("requests", title="Total Requests")
    .build()
)

# Monitor agents
tracker = SessionTracker()
agent = tracker.create_agent("coder-1")
agent.set_status(AgentStatus.RUNNING)
agent.update_context(85_000)

# Set up alerts
alerts = AlertManager(engine.collector)
alerts.add_rule(AlertRule(
    metric="cpu",
    condition=Condition.GT,
    threshold=90,
    severity=Severity.CRITICAL,
))
fired = alerts.check()
```

## Configuration

Copy `.env.example` to `.env` and customise:

| Variable | Default | Description |
|---|---|---|
| `MJOLNIR_DASHBOARD_NAME` | `mjolnir` | Default dashboard name |
| `MJOLNIR_REFRESH_INTERVAL` | `5` | Refresh interval in seconds |
| `MJOLNIR_MAX_HISTORY` | `10000` | Max metric samples retained |
| `MJOLNIR_LOG_LEVEL` | `INFO` | Logging verbosity |

## Live Demo

Visit the landing page: **https://MukundaKatta.github.io/mjolnir/**

## License

MIT License -- Officethree Technologies

## Part of the Mythological Portfolio

This is project **mjolnir** in the [100-project Mythological Portfolio](https://github.com/MukundaKatta) by Officethree Technologies.
