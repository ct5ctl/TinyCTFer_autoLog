""""""
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
_debug_log("toolset.__init__ entry", "toolset/__init__.py:1", "A", {"step":"start"})
# #endregion
from core import namespace

namespace()

_debug_log("after namespace()", "toolset/__init__.py:5", "A,D")

from .proxy import proxy
from .terminal import terminal
from .browser import browser
from .note import note
_debug_log("before logger import", "toolset/__init__.py:10", "A,C")
try:
    from .logger import logger
    _debug_log("logger import succeeded", "toolset/__init__.py:12", "A", {"logger_exists":logger is not None,"logger_type":str(type(logger)) if logger else "None"})
except Exception as e:
    _debug_log("logger import failed", "toolset/__init__.py:14", "A,B", {"error":str(e),"error_type":type(e).__name__})
    logger = None
    _debug_log("logger set to None", "toolset/__init__.py:15", "A,B")

# Ensure logger is always defined, even if import failed
if 'logger' not in globals():
    logger = None
    _debug_log("logger not in globals, setting to None", "toolset/__init__.py:18", "A,B")

__all__ = ["proxy", "terminal", "browser", "note", "logger"]
_debug_log("toolset.__init__ exit", "toolset/__init__.py:20", "A", {"has_logger":"logger" in globals(),"logger_value":str(logger) if 'logger' in globals() else "UNDEFINED"})
# #endregion
