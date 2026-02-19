"""PyInstaller runtime hook: patch python-hwpx ET reference bug.

The python-hwpx package (hwpx/document.py) references ``ET`` without
importing ``xml.etree.ElementTree as ET``.  This hook ensures the
symbol exists before the module is loaded.
"""
import xml.etree.ElementTree as ET  # noqa: F401
import sys

_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
