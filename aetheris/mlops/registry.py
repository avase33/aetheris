"""Model registry + drift/retrain event log (SQLite)."""

from __future__ import annotations

import json
import sqlite3
import time

from ..common.models import DriftReport

_SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
  name TEXT, version TEXT, status TEXT, accuracy REAL, created_at REAL,
  PRIMARY KEY (name, version)
);
CREATE TABLE IF NOT EXISTS drift_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT, report TEXT, created_at REAL
);
"""


class ModelRegistry:
    def __init__(self, path: str = "aetheris-mlops.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def register(self, name: str, version: str, accuracy: float, status: str = "active") -> None:
        # New active version supersedes the previous one.
        self.conn.execute("UPDATE models SET status='superseded' WHERE name=? AND status='active'", (name,))
        self.conn.execute("INSERT OR REPLACE INTO models VALUES (?,?,?,?,?)",
                          (name, version, status, accuracy, time.time()))
        self.conn.commit()

    def active(self, name: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM models WHERE name=? AND status='active'", (name,)).fetchone()
        return dict(row) if row else None

    def versions(self, name: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM models WHERE name=? ORDER BY created_at DESC", (name,)).fetchall()
        return [dict(r) for r in rows]

    def record_drift(self, report: DriftReport) -> None:
        self.conn.execute("INSERT INTO drift_events (model, report, created_at) VALUES (?,?,?)",
                          (report.model, json.dumps(report.to_dict()), time.time()))
        self.conn.commit()

    def drift_history(self, model: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT report, created_at FROM drift_events WHERE model=? ORDER BY created_at DESC LIMIT ?",
            (model, limit)).fetchall()
        return [{**json.loads(r["report"]), "created_at": r["created_at"]} for r in rows]

    def close(self) -> None:
        self.conn.close()
