#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

_current_dir = Path(__file__).parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from src.server import main

if __name__ == "__main__":
    main()
