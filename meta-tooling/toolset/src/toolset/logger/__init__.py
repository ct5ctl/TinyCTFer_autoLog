"""
Structured penetration-testing logger exposed via toolset.logger.
"""
from core import namespace, tool, toolset

namespace()

from .logger import PenetrationLogger

_logger_instance = PenetrationLogger()


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


