"""Tests for mjolnir.agents -- agent monitoring and session tracking."""

from mjolnir.agents import AgentMonitor, AgentSnapshot, AgentStatus, SessionTracker


class TestAgentSnapshot:
    def test_context_pct(self):
        snap = AgentSnapshot(agent_id="a1", context_used=50_000, context_limit=200_000)
        assert snap.context_pct == 25.0

    def test_context_pct_zero_limit(self):
        snap = AgentSnapshot(agent_id="a1", context_limit=0)
        assert snap.context_pct == 0.0

    def test_todo_pct(self):
        snap = AgentSnapshot(agent_id="a1", todos_total=10, todos_done=7)
        assert snap.todo_pct == 70.0

    def test_to_dict(self):
        snap = AgentSnapshot(agent_id="a1", tool_calls=5)
        d = snap.to_dict()
        assert d["agent_id"] == "a1"
        assert d["tool_calls"] == 5


class TestAgentMonitor:
    def test_lifecycle(self):
        mon = AgentMonitor(agent_id="test-1")
        assert mon.status == AgentStatus.IDLE
        mon.set_status(AgentStatus.RUNNING)
        mon.update_context(80_000)
        mon.record_tool_call(3)
        mon.set_todos(5, 2)
        snap = mon.snapshot()
        assert snap.status == AgentStatus.RUNNING
        assert snap.context_used == 80_000
        assert snap.tool_calls == 3
        assert snap.todos_done == 2

    def test_history(self):
        mon = AgentMonitor(agent_id="h1")
        mon.snapshot()
        mon.record_tool_call()
        mon.snapshot()
        assert len(mon.history) == 2

    def test_auto_id(self):
        mon = AgentMonitor()
        assert mon.agent_id.startswith("agent-")


class TestSessionTracker:
    def test_create_and_list(self):
        t = SessionTracker()
        t.create_agent("alpha")
        t.create_agent("beta")
        assert set(t.list_agents()) == {"alpha", "beta"}

    def test_get_and_remove(self):
        t = SessionTracker()
        t.create_agent("x")
        assert t.get("x") is not None
        assert t.remove("x") is True
        assert t.get("x") is None

    def test_active_count(self):
        t = SessionTracker()
        a = t.create_agent("a")
        b = t.create_agent("b")
        a.set_status(AgentStatus.RUNNING)
        assert t.active_count == 1

    def test_summary(self):
        t = SessionTracker()
        t.create_agent("s1")
        s = t.summary()
        assert s["total_agents"] == 1
        assert "s1" in s["agents"]
