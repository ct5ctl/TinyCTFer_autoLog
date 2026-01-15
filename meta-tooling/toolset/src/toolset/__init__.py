""""""
from core import namespace

namespace()

from .proxy import proxy
from .terminal import terminal
from .browser import browser
from .note import note
from .logger import logger

__all__ = ["proxy", "terminal", "browser", "note", "logger"]
