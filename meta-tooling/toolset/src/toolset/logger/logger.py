import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class PenetrationLogger:
    """
    Structured logger for penetration testing steps.

    Log schema:
    {
        "initial_prompt": "XXX",
        "steps": [
            {
                "step_number": 1,
                "planning": "XXX",
                "code": "XXX",
                "observation": [
                    {"observation_raw": "XXX", "observation_type": "type_a"},
                    {"observation_raw": "XXX", "observation_type": "type_b"}
                ]
            }
        ],
        "final_report": "XXX"
    }
    """

    def __init__(self) -> None:
        # workspace in container is /home/ubuntu/Workspace
        workspace_dir = os.getenv("WORKSPACE_DIR", str(Path.home() / "Workspace"))
        self._logs_dir = os.path.join(workspace_dir, "logs")
        os.makedirs(self._logs_dir, exist_ok=True)

        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "initial_prompt": "",
            "steps": [],
            "final_report": "",
        }
        self._current_step_index: Optional[int] = None

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._filepath = os.path.join(self._logs_dir, f"penetration_log_{ts}.json")

    # ---- core helpers ----
    def _ensure_step(self) -> int:
        """
        Ensure there is an active step; if not, create a new one.
        Returns current step index.
        """
        if self._current_step_index is None:
            step_number = len(self._data["steps"]) + 1
            self._data["steps"].append(
                {
                    "step_number": step_number,
                    "planning": "",
                    "code": "",
                    "observation": [],
                }
            )
            self._current_step_index = len(self._data["steps"]) - 1
        return self._current_step_index

    def _append_observation(self, obs: Dict[str, Any]) -> None:
        idx = self._ensure_step()
        self._data["steps"][idx]["observation"].append(obs)

    def _dump(self) -> None:
        tmp_path = self._filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._filepath)

    # ---- public API ----
    def set_initial_prompt(self, prompt: str) -> None:
        with self._lock:
            self._data["initial_prompt"] = prompt
            self._dump()

    def next_step(self) -> int:
        """
        Manually start a new step; returns its step_number.
        """
        with self._lock:
            step_number = len(self._data["steps"]) + 1
            self._data["steps"].append(
                {
                    "step_number": step_number,
                    "planning": "",
                    "code": "",
                    "observation": [],
                }
            )
            self._current_step_index = len(self._data["steps"]) - 1
            self._dump()
            return step_number

    def log_planning(self, planning_text: str) -> None:
        with self._lock:
            idx = self._ensure_step()
            self._data["steps"][idx]["planning"] = planning_text
            self._dump()

    def log_code(self, code: str) -> None:
        with self._lock:
            idx = self._ensure_step()
            self._data["steps"][idx]["code"] = code
            self._dump()

    def log_observation(
        self,
        raw_data: Any,
        obs_type: str,
    ) -> None:
        """
        Log an observation with explicit type.
        """
        with self._lock:
            obs = {
                "observation_raw": raw_data,
                "observation_type": obs_type,
            }
            self._append_observation(obs)
            self._dump()

    def auto_observation(
        self,
        raw_data: Any,
        default_type: str = "code_output",
    ) -> None:
        """
        Convenience wrapper: try to infer observation_type from context,
        fall back to default_type.
        """
        inferred_type = default_type
        if isinstance(raw_data, str):
            lower = raw_data.lower()
            if "<html" in lower or "<!doctype html" in lower:
                inferred_type = "webpage_source"
            elif "http/" in lower and "host:" in lower:
                inferred_type = "http_traffic"
        self.log_observation(raw_data, inferred_type)

    def set_final_report(self, report: str) -> None:
        with self._lock:
            self._data["final_report"] = report
            self._dump()

    # ---- inspection helpers (not used by tools directly) ----
    def get_log(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))

    def get_filepath(self) -> str:
        return self._filepath

