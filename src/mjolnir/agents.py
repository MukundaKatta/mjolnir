"""Agent monitoring subsystem for Mjolnir.

Tracks AI coding agent sessions -- status, context window usage,
tool invocations, and to-do progress.  Think of each agent as a
warrior in Asgard: Mjolnir keeps watch so none fall unnoticed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Agent status
# ---------------------------------------------------------------------------

class AgentStatus(Enum):
    """Lifecycle states an agent session may be in."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# AgentSnapshot -- point-in-time view of a single agent
# ---------------------------------------------------------------------------

@dataclass
class AgentSnapshot:
    """Immutable point-in-time capture of agent state.

    Attributes:
        agent_id:       Unique agent identifier.
        status:         Current lifecycle status.
        context_used:   Tokens consumed in the context window.
        context_limit:  Maximum context window size.
        tool_calls:     Number of tool invocations so far.
        todos_total:    Total to-do items in the session.
        todos_done:     Completed to-do items.
        uptime:         Seconds since the agent session started.
        metadata:       Arbitrary extra information.
        captured_at:    Unix timestamp of this snapshot.
    """
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    context_used: int = 0
    context_limit: int = 200_000
    tool_calls: int = 0
    todos_total: int = 0
    todos_done: int = 0
    uptime: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    captured_at: float = 0.0

    def __post_init__(self) -> None:
        if self.captured_at == 0.0:
            self.captured_at = time.time()

    @property
    def context_pct(self) -> float:
        """Percentage of context window consumed."""
        if self.context_limit <= 0:
            return 0.0
        return round(self.context_used / self.context_limit * 100, 2)

    @property
    def todo_pct(self) -> float:
        """Percentage of to-do items completed."""
        if self.todos_total <= 0:
            return 0.0
        return round(self.todos_done / self.todos_total * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "context_used": self.context_used,
            "context_limit": self.context_limit,
            "context_pct": self.context_pct,
            "tool_calls": self.tool_calls,
            "todos_total": self.todos_total,
            "todos_done": self.todos_done,
            "todo_pct": self.todo_pct,
            "uptime": self.uptime,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# AgentMonitor -- mutable live tracker for a single agent
# ---------------------------------------------------------------------------

class AgentMonitor:
    """Mutable tracker for a single AI agent session.

    Records status transitions, context usage, tool calls, and to-do
    progress.  Call :meth:`snapshot` at any time to freeze current state.
    """

    def __init__(self, agent_id: Optional[str] = None, context_limit: int = 200_000) -> None:
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.status = AgentStatus.IDLE
        self.context_used = 0
        self.context_limit = context_limit
        self.tool_calls = 0
        self.todos_total = 0
        self.todos_done = 0
        self._start_time = time.time()
        self.metadata: Dict[str, Any] = {}
        self._history: List[AgentSnapshot] = []

    def set_status(self, status: AgentStatus) -> None:
        self.status = status

    def update_context(self, tokens_used: int) -> None:
        self.context_used = tokens_used

    def record_tool_call(self, count: int = 1) -> None:
        self.tool_calls += count

    def set_todos(self, total: int, done: int) -> None:
        self.todos_total = total
        self.todos_done = done

    def snapshot(self) -> AgentSnapshot:
        snap = AgentSnapshot(
            agent_id=self.agent_id,
            status=self.status,
            context_used=self.context_used,
            context_limit=self.context_limit,
            tool_calls=self.tool_calls,
            todos_total=self.todos_total,
            todos_done=self.todos_done,
            uptime=time.time() - self._start_time,
            metadata=dict(self.metadata),
        )
        self._history.append(snap)
        return snap

    @property
    def history(self) -> List[AgentSnapshot]:
        return list(self._history)


# ---------------------------------------------------------------------------
# SessionTracker -- manages multiple agents
# ---------------------------------------------------------------------------

class SessionTracker:
    """Registry that manages many :class:`AgentMonitor` instances.

    Provides look-up by agent id, enumeration, and a combined summary.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentMonitor] = {}

    def register(self, monitor: AgentMonitor) -> None:
        self._agents[monitor.agent_id] = monitor

    def create_agent(self, agent_id: Optional[str] = None, context_limit: int = 200_000) -> AgentMonitor:
        mon = AgentMonitor(agent_id=agent_id, context_limit=context_limit)
        self.register(mon)
        return mon

    def get(self, agent_id: str) -> Optional[AgentMonitor]:
        return self._agents.get(agent_id)

    def remove(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    @property
    def active_count(self) -> int:
        return sum(1 for m in self._agents.values() if m.status == AgentStatus.RUNNING)

    def summary(self) -> Dict[str, Any]:
        snapshots = {aid: m.snapshot().to_dict() for aid, m in self._agents.items()}
        return {
            "total_agents": len(self._agents),
            "active_agents": self.active_count,
            "agents": snapshots,
        }
