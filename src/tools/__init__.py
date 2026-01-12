"""
HWP MCP Tools Package
각종 도구 모듈을 포함 (pyhwp 기반)
"""

try:
    from .pyhwp_adapter import (
        PyhwpAdapter,
        get_pyhwp_adapter,
        reset_pyhwp_adapter,
        is_hwp_file,
    )
except ImportError:
    pass
from .chart_tools import register_chart_tools
from .equation_tools import register_equation_tools
from .document_tools import register_document_tools
from .template_tools import register_template_tools

from .hwp_controller_base import (
    HwpControllerBase,
    Platform,
    Capability,
    HwpError,
    NotSupportedError,
    DocumentInfo,
    Position,
    TableInfo,
    get_current_platform,
)
from .controller_factory import (
    get_controller,
    reset_controller,
    get_platform_info,
    check_capability,
    get_capability_matrix,
)
from .unified_tools import register_unified_tools

__all__ = [
    "PyhwpAdapter",
    "get_pyhwp_adapter",
    "reset_pyhwp_adapter",
    "is_hwp_file",
    "register_chart_tools",
    "register_equation_tools",
    "register_document_tools",
    "register_template_tools",
    "HwpControllerBase",
    "Platform",
    "Capability",
    "HwpError",
    "NotSupportedError",
    "DocumentInfo",
    "Position",
    "TableInfo",
    "get_current_platform",
    "get_controller",
    "reset_controller",
    "get_platform_info",
    "check_capability",
    "get_capability_matrix",
    "register_unified_tools",
]
