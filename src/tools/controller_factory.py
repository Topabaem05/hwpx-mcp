from __future__ import annotations

import importlib
import sys


_REAL_MODULE_NAME = "hwpx_mcp.tools.controller_factory"
_real_module = importlib.import_module(_REAL_MODULE_NAME)

for _name in dir(_real_module):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_real_module, _name)

sys.modules[__name__] = _real_module
