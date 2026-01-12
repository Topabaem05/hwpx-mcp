import pytest
from unittest.mock import patch, MagicMock

from src.tools.controller_factory import (
    get_controller,
    reset_controller,
    get_platform_info,
    check_capability,
    get_capability_matrix,
)
from src.tools.hwp_controller_base import Platform, Capability


class TestGetPlatformInfo:
    def test_returns_dict(self):
        info = get_platform_info()
        assert isinstance(info, dict)
        assert "platform" in info
        assert "is_windows" in info
        assert "capabilities" in info


class TestGetCapabilityMatrix:
    def test_returns_matrix(self):
        matrix = get_capability_matrix()
        assert isinstance(matrix, dict)
        assert Capability.CREATE_DOCUMENT.value in matrix

    def test_matrix_has_platform_keys(self):
        matrix = get_capability_matrix()
        for cap_name, support in matrix.items():
            assert "windows" in support
            assert "cross_platform" in support

    def test_windows_supports_all(self):
        matrix = get_capability_matrix()
        for cap_name, support in matrix.items():
            assert support["windows"] is True


class TestCheckCapability:
    @patch("src.tools.controller_factory.get_controller")
    def test_check_supported_capability(self, mock_get):
        mock_controller = MagicMock()
        mock_controller.supports.return_value = True
        mock_get.return_value = mock_controller

        result = check_capability(Capability.CREATE_DOCUMENT)
        assert result is True

    @patch("src.tools.controller_factory.get_controller")
    def test_check_unsupported_capability(self, mock_get):
        mock_controller = MagicMock()
        mock_controller.supports.return_value = False
        mock_get.return_value = mock_controller

        result = check_capability(Capability.SAVE_AS_PDF)
        assert result is False


class TestResetController:
    @patch("src.tools.controller_factory._controller_instance", None)
    def test_reset_when_none(self):
        reset_controller()

    @patch("src.tools.controller_factory._controller_instance")
    def test_reset_calls_disconnect(self, mock_instance):
        mock_instance.disconnect = MagicMock()
        reset_controller()
