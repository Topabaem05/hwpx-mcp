"""
Controller Factory - Platform detection and controller instantiation.
Provides unified interface for getting the appropriate HWP controller based on platform.
"""

import logging
from typing import Optional, Dict, Any, Type

from .hwp_controller_base import (
    HwpControllerBase,
    Platform,
    Capability,
    get_current_platform,
    HwpError,
)

logger = logging.getLogger("hwp-mcp.factory")

# Global controller instance (singleton pattern)
_controller_instance: Optional[HwpControllerBase] = None


def get_controller(
    platform: Optional[Platform] = None,
    force_new: bool = False,
    **kwargs,
) -> HwpControllerBase:
    """
    Get the appropriate HWP controller for the current or specified platform.

    Args:
        platform: Force a specific platform (auto-detected if None)
        force_new: Create new instance even if one exists
        **kwargs: Additional arguments passed to controller constructor

    Returns:
        HwpControllerBase: Platform-appropriate controller instance

    Raises:
        HwpError: If controller cannot be created
    """
    global _controller_instance

    if _controller_instance is not None and not force_new:
        return _controller_instance

    target_platform = platform or get_current_platform()

    if target_platform == Platform.WINDOWS:
        _controller_instance = _create_windows_controller(**kwargs)
    else:
        _controller_instance = _create_cross_platform_controller(**kwargs)

    return _controller_instance


def _create_windows_controller(**kwargs) -> HwpControllerBase:
    """Create Windows HWP controller using pyhwpx."""
    try:
        from .windows_hwp_controller_v2 import WindowsHwpControllerV2

        controller = WindowsHwpControllerV2(**kwargs)
        logger.info("Created WindowsHwpControllerV2")
        return controller
    except ImportError as e:
        logger.error(f"Failed to import WindowsHwpControllerV2: {e}")
        raise HwpError(
            "WindowsHwpControllerV2 not available. "
            "Ensure you are on Windows with pyhwpx installed."
        ) from e


def _create_cross_platform_controller(**kwargs) -> HwpControllerBase:
    """Create cross-platform HWPX controller using python-hwpx."""
    try:
        from .cross_platform_controller import CrossPlatformHwpxController

        controller = CrossPlatformHwpxController(**kwargs)
        logger.info("Created CrossPlatformHwpxController")
        return controller
    except ImportError as e:
        logger.error(f"Failed to import CrossPlatformHwpxController: {e}")
        raise HwpError(
            "CrossPlatformHwpxController not available. "
            "Ensure python-hwpx is installed."
        ) from e


def reset_controller() -> None:
    """Reset the global controller instance."""
    global _controller_instance
    if _controller_instance is not None:
        try:
            _controller_instance.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting controller: {e}")
        _controller_instance = None
    logger.info("Controller reset")


def get_platform_info() -> Dict[str, Any]:
    """
    Get information about the current platform and available capabilities.

    Returns:
        Dict containing platform info and available capabilities
    """
    current = get_current_platform()

    # Try to get actual controller capabilities
    try:
        controller = get_controller()
        capabilities = [cap.value for cap in controller.capabilities]
        is_connected = controller.is_connected
        has_document = controller.has_document
    except Exception:
        capabilities = []
        is_connected = False
        has_document = False

    return {
        "platform": current.value,
        "is_windows": current == Platform.WINDOWS,
        "is_connected": is_connected,
        "has_document": has_document,
        "capabilities": capabilities,
        "capability_count": len(capabilities),
        "controller_type": (
            "WindowsHwpControllerV2"
            if current == Platform.WINDOWS
            else "CrossPlatformHwpxController"
        ),
    }


def check_capability(capability: Capability) -> bool:
    """
    Check if a specific capability is available on the current platform.

    Args:
        capability: The capability to check

    Returns:
        bool: True if capability is supported
    """
    try:
        controller = get_controller()
        return controller.supports(capability)
    except Exception:
        return False


def get_capability_matrix() -> Dict[str, Dict[str, bool]]:
    """
    Get a matrix of all capabilities and their support status per platform.

    Returns:
        Dict mapping capability names to platform support status
    """
    matrix = {}

    for cap in Capability:
        matrix[cap.value] = {
            "windows": True,  # pyhwpx supports all
            "cross_platform": cap
            in {
                # Only capabilities supported by python-hwpx
                Capability.CREATE_DOCUMENT,
                Capability.SAVE_DOCUMENT,
                Capability.SAVE_AS_HWPX,
                Capability.INSERT_TEXT,
                Capability.CREATE_TABLE,
                Capability.INSERT_PICTURE,
                Capability.SET_FONT,
                Capability.GET_PAGE_COUNT,
                Capability.GET_DOCUMENT_INFO,
            },
        }

    return matrix
