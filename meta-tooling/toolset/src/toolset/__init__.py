""""""
# #region agent log
import json
import os
try:
    with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"toolset/__init__.py:1","message":"toolset.__init__ entry","data":{"step":"start"},"timestamp":int(__import__("time").time()*1000)}) + "\n")
except: pass
# #endregion
from core import namespace

namespace()

# #region agent log
try:
    with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,D","location":"toolset/__init__.py:5","message":"after namespace()","data":{},"timestamp":int(__import__("time").time()*1000)}) + "\n")
except: pass
# #endregion

from .proxy import proxy
from .terminal import terminal
from .browser import browser
from .note import note
# #region agent log
try:
    with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,C","location":"toolset/__init__.py:10","message":"before logger import","data":{},"timestamp":int(__import__("time").time()*1000)}) + "\n")
except: pass
# #endregion
try:
    from .logger import logger
    # #region agent log
    try:
        with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"toolset/__init__.py:12","message":"logger import succeeded","data":{"logger_exists":logger is not None,"logger_type":str(type(logger))},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,B","location":"toolset/__init__.py:14","message":"logger import failed","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    except: pass
    # #endregion
    logger = None

__all__ = ["proxy", "terminal", "browser", "note", "logger"]
# #region agent log
try:
    with open(r"e:\_Papers\_Paper Works\2512pentest\TinyCTFer_autoLog\.cursor\debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"toolset/__init__.py:20","message":"toolset.__init__ exit","data":{"has_logger":hasattr(__import__(__name__), "logger")},"timestamp":int(__import__("time").time()*1000)}) + "\n")
except: pass
# #endregion