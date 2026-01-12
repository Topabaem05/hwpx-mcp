import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from src.tools.hwp_controller_base import (
    HwpControllerBase,
    Platform,
    Capability,
    HwpError,
    NotSupportedError,
    ConnectionError,
    DocumentNotOpenError,
    DocumentInfo,
    Position,
    TableInfo,
    get_current_platform,
)


class TestPlatformEnum:
    def test_platform_values(self):
        assert Platform.WINDOWS.value == "windows"
        assert Platform.CROSS_PLATFORM.value == "cross_platform"


class TestCapabilityEnum:
    def test_core_capabilities_exist(self):
        assert Capability.CREATE_DOCUMENT
        assert Capability.OPEN_DOCUMENT
        assert Capability.SAVE_DOCUMENT
        assert Capability.INSERT_TEXT
        assert Capability.CREATE_TABLE

    def test_capability_count(self):
        assert len(Capability) >= 40


class TestExceptions:
    def test_hwp_error(self):
        with pytest.raises(HwpError):
            raise HwpError("test error")

    def test_not_supported_error(self):
        err = NotSupportedError(
            "Feature not supported",
            capability=Capability.CREATE_DOCUMENT,
            current_platform=Platform.CROSS_PLATFORM,
        )
        assert err.capability == Capability.CREATE_DOCUMENT
        assert err.current_platform == Platform.CROSS_PLATFORM

    def test_connection_error(self):
        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection failed")

    def test_document_not_open_error(self):
        with pytest.raises(DocumentNotOpenError):
            raise DocumentNotOpenError("No document")


class TestDataClasses:
    def test_document_info_defaults(self):
        info = DocumentInfo()
        assert info.path is None
        assert info.page_count == 0
        assert info.is_empty is True

    def test_document_info_values(self):
        info = DocumentInfo(
            path="/test/doc.hwpx",
            title="Test",
            page_count=5,
            is_modified=True,
            is_empty=False,
            format="hwpx",
        )
        assert info.path == "/test/doc.hwpx"
        assert info.page_count == 5

    def test_position_defaults(self):
        pos = Position()
        assert pos.list_id == 0
        assert pos.para_id == 0
        assert pos.char_index == 0

    def test_table_info(self):
        info = TableInfo(rows=3, cols=4)
        assert info.rows == 3
        assert info.cols == 4


class TestGetCurrentPlatform:
    def test_returns_platform_enum(self):
        result = get_current_platform()
        assert isinstance(result, Platform)

    @patch("platform.system", return_value="Windows")
    def test_windows_detection(self, mock_system):
        from src.tools.hwp_controller_base import get_current_platform

        result = get_current_platform()
        assert result == Platform.WINDOWS

    @patch("platform.system", return_value="Darwin")
    def test_macos_detection(self, mock_system):
        from src.tools.hwp_controller_base import get_current_platform

        result = get_current_platform()
        assert result == Platform.CROSS_PLATFORM


class ConcreteController(HwpControllerBase):
    def __init__(self):
        self._connected = False
        self._has_doc = False
        self._text = ""

    @property
    def platform(self) -> Platform:
        return Platform.CROSS_PLATFORM

    @property
    def capabilities(self) -> set:
        return {Capability.CREATE_DOCUMENT, Capability.INSERT_TEXT}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def has_document(self) -> bool:
        return self._has_doc

    def connect(self, visible: bool = True) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def create_document(self) -> bool:
        self._has_doc = True
        return True

    def open_document(self, path: str) -> bool:
        self._has_doc = True
        return True

    def save_document(self, path: str = None) -> bool:
        return True

    def save_as(self, path: str, format: str = "hwpx") -> bool:
        return True

    def close_document(self, save: bool = False) -> bool:
        self._has_doc = False
        return True

    def insert_text(self, text: str) -> bool:
        self._text += text
        return True

    def get_text(self) -> str:
        return self._text

    def create_table(self, rows: int, cols: int, data=None) -> bool:
        return True

    def get_page_count(self) -> int:
        return 1

    def get_document_info(self) -> DocumentInfo:
        return DocumentInfo()


class TestHwpControllerBase:
    def test_supports_capability(self):
        controller = ConcreteController()
        assert controller.supports(Capability.CREATE_DOCUMENT)
        assert controller.supports(Capability.INSERT_TEXT)
        assert not controller.supports(Capability.SAVE_AS_PDF)

    def test_require_capability_passes(self):
        controller = ConcreteController()
        controller.require_capability(Capability.CREATE_DOCUMENT)

    def test_require_capability_raises(self):
        controller = ConcreteController()
        with pytest.raises(NotSupportedError):
            controller.require_capability(Capability.SAVE_AS_PDF)

    def test_require_connection_raises(self):
        controller = ConcreteController()
        with pytest.raises(ConnectionError):
            controller.require_connection()

    def test_require_connection_passes(self):
        controller = ConcreteController()
        controller.connect()
        controller.require_connection()

    def test_require_document_raises(self):
        controller = ConcreteController()
        controller.connect()
        with pytest.raises(DocumentNotOpenError):
            controller.require_document()

    def test_require_document_passes(self):
        controller = ConcreteController()
        controller.connect()
        controller.create_document()
        controller.require_document()

    def test_full_workflow(self):
        controller = ConcreteController()

        assert controller.connect()
        assert controller.is_connected

        assert controller.create_document()
        assert controller.has_document

        assert controller.insert_text("Hello ")
        assert controller.insert_text("World")
        assert controller.get_text() == "Hello World"

        assert controller.save_document("/test.hwpx")
        assert controller.close_document()
        assert not controller.has_document

        assert controller.disconnect()
        assert not controller.is_connected
