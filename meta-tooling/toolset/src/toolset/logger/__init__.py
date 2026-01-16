"""
Structured penetration-testing logger exposed via toolset.logger.
"""
# #region agent log
import json
import os
def _debug_log(msg, loc, hyp, data=None):
    try:
        debug_log_path = os.path.join(os.getenv("WORKSPACE_DIR", "/home/ubuntu/Workspace"), ".cursor", "debug.log")
        os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
        with open(debug_log_path, "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":hyp,"location":loc,"message":msg,"data":data or {},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    except: pass
_debug_log("logger/__init__ entry", "toolset/logger/__init__.py:1", "B,C")
# #endregion
from core import namespace, tool, toolset

_debug_log("before namespace()", "toolset/logger/__init__.py:8", "B,C")
namespace()

_debug_log("before PenetrationLogger import", "toolset/logger/__init__.py:11", "B")
from .logger import PenetrationLogger

_debug_log("before PenetrationLogger()", "toolset/logger/__init__.py:14", "B")
try:
    _logger_instance = PenetrationLogger()
    _debug_log("PenetrationLogger() succeeded", "toolset/logger/__init__.py:17", "B", {"instance_type":str(type(_logger_instance))})
except Exception as e:
    _debug_log("PenetrationLogger() failed", "toolset/logger/__init__.py:20", "B", {"error":str(e),"error_type":type(e).__name__})
    raise


@toolset()
class LoggerTools:
    """
    Tool wrapper so the agent can explicitly log planning and final report.
    """

    def __init__(self) -> None:
        # reuse global logger instance so all tools share one log file
        self._logger = _logger_instance

    @tool()
    def log_planning(self, planning: str) -> str:
        """
        Log a planning string for the current or next step.
        """
        # start a new step if current planning already exists
        log = self._logger.get_log()
        if log["steps"] and log["steps"][-1].get("planning"):
            self._logger.next_step()
        self._logger.log_planning(planning)
        return "planning logged"

    @tool()
    def log_final_report(self, report: str) -> str:
        """
        Log final report for the engagement.
        """
        self._logger.set_final_report(report)
        return "final_report logged"


logger = _logger_instance
logger_tools = LoggerTools()

__all__ = ["logger", "logger_tools", "PenetrationLogger"]

