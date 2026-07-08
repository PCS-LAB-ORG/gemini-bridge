"""
gemini_bridge/tools/__init__.py
---------------------------------
Tool package root — re-exports all MCP tool registration callables.

Responsibilities:
  - Collect tool modules into a single importable namespace

Design notes:
  - Open/Closed: new tools add a module here + one import line — server.py unchanged

Used by:  server.py (registers all tools)
Imports:  tools/ask.py, tools/brainstorm.py, tools/review.py, tools/debug.py, tools/architect.py
"""

from gemini_bridge.tools.architect import register as register_architect
from gemini_bridge.tools.ask import register as register_ask
from gemini_bridge.tools.brainstorm import register as register_brainstorm
from gemini_bridge.tools.debug import register as register_debug
from gemini_bridge.tools.list_models import register as register_list_models
from gemini_bridge.tools.review import register as register_review

__all__ = [
    "register_ask",
    "register_brainstorm",
    "register_review",
    "register_debug",
    "register_architect",
    "register_list_models",
]
