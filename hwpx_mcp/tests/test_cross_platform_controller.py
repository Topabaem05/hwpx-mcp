import pytest
from unittest.mock import patch, MagicMock

from hwpx_mcp.tools.cross_platform_controller import (
    CrossPlatformHwpxController,
    CROSS_PLATFORM_CAPABILITIES,
)
from hwpx_mcp.tools.hwp_controller_base import (
    Platform,
    Capability,
    NotSupportedError,
    HwpError,
)


class TestCrossPlatformCapabilities:
    def test_supported_capabilities(self):
        assert Capability.CREATE_DOCUMENT in CROSS_PLATFORM_CAPABILITIES
        assert Capability.SAVE_DOCUMENT in CROSS_PLATFORM_CAPABILITIES
        assert Capability.INSERT_TEXT in CROSS_PLATFORM_CAPABILITIES
        assert Capability.CREATE_TABLE in CROSS_PLATFORM_CAPABILITIES

    def test_unsupported_capabilities(self):
        assert Capability.OPEN_DOCUMENT not in CROSS_PLATFORM_CAPABILITIES
        assert Capability.SAVE_AS_PDF not in CROSS_PLATFORM_CAPABILITIES
        assert Capability.RUN_ACTION not in CROSS_PLATFORM_CAPABILITIES


class TestCrossPlatformController:
    def test_platform_is_cross_platform(self):
        controller = CrossPlatformHwpxController()
        assert controller.platform == Platform.CROSS_PLATFORM

    def test_connect_always_succeeds(self):
        controller = CrossPlatformHwpxController()
        assert controller.connect() is True
        assert controller.is_connected is True

    def test_disconnect(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.disconnect() is True
        assert controller.has_document is False

    def test_create_document(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        assert controller.create_document() is True
        assert controller.has_document is True

    def test_open_document_raises_not_supported(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        with pytest.raises(NotSupportedError):
            controller.open_document("/some/path.hwpx")

    def test_insert_text(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.insert_text("Hello World") is True

    def test_get_text(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        controller.insert_text("Test content")
        text = controller.get_text()
        assert "Test content" in text

    def test_create_table(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.create_table(rows=3, cols=4) is True

    def test_create_table_with_data(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        data = [["A", "B"], ["1", "2"]]
        assert controller.create_table(rows=2, cols=2, data=data) is True

    def test_is_modified_tracking(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.is_modified() is False
        controller.insert_text("Changes")
        assert controller.is_modified() is True

    def test_is_empty(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.is_empty() is True
        controller.insert_text("Content")
        assert controller.is_empty() is False

    def test_get_document_info(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        info = controller.get_document_info()
        assert info.format == "hwpx"
        assert info.is_empty is True

    def test_save_as_non_hwpx_raises(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        with pytest.raises(NotSupportedError):
            controller.save_as("/test.pdf", format="pdf")

    def test_add_heading(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.add_heading("Title", level=1) is True

    def test_add_paragraph(self):
        controller = CrossPlatformHwpxController()
        controller.connect()
        controller.create_document()
        assert controller.add_paragraph("Para text") is True
