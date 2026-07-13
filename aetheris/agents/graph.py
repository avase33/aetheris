"""A minimal async state-graph (LangGraph-style) for the self-healing workflow.

Nodes are async functions over a shared state; edges may be conditional, which is
what enables the diagnose → plan → act → verify → (retry|escalate) loop.
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Generic, TypeVar

S = TypeVar("S")
END = "__end__"


class StateGraph(Generic[S]):
    def __init__(self) -> None:
        self._nodes: dict[str, Callable[[S], Awaitable[Any]]] = {}
        self._edges: dict[str, str] = {}
        self._cond: dict[str, Callable[[S], str]] = {}
        self._entry: str | None = None

    def add_node(self, name, fn):
        if not inspect.iscoroutinefunction(fn):
            raise ValueError(f"node '{name}' must be async")
        self._nodes[name] = fn
        return self

    def set_entry_point(self, name):
        self._entry = name
        return self

    def add_edge(self, a, b):
        self._edges[a] = b
        return self

    def add_conditional_edges(self, a, router):
        self._cond[a] = router
        return self

    def compile(self):
        return _Compiled(self._nodes, self._edges, self._cond, self._entry)


class _Compiled(Generic[S]):
    def __init__(self, nodes, edges, cond, entry, max_steps: int = 50):
        self.nodes, self.edges, self.cond, self.entry, self.max_steps = nodes, edges, cond, entry, max_steps

    def _next(self, name, state):
        if name in self.cond:
            return self.cond[name](state)
        return self.edges.get(name, END)

    async def invoke(self, state: S) -> S:
        cur, steps = self.entry, 0
        while cur != END:
            if steps >= self.max_steps:
                raise RuntimeError("graph exceeded step budget")
            steps += 1
            res = await self.nodes[cur](state)
            if res is not None:
                state = res
            cur = self._next(cur, state)
        return state
