"""
Cross-Platform HWPX Controller - Implements HwpControllerBase using python-hwpx library.
Works on macOS, Linux, and Windows. Limited to HWPX format creation and editing.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Set
import tempfile

from .hwp_controller_base import (
    HwpControllerBase,
    Platform,
    Capability,
    HwpError,
    NotSupportedError,
    DocumentInfo,
    Position,
)
from .hwpx_builder import HwpxBuilder

logger = logging.getLogger("hwp-mcp.cross_platform_controller")

CROSS_PLATFORM_CAPABILITIES: Set[Capability] = {
    Capability.CREATE_DOCUMENT,
    Capability.SAVE_DOCUMENT,
    Capability.SAVE_AS_HWPX,
    Capability.INSERT_TEXT,
    Capability.CREATE_TABLE,
    Capability.TABLE_FROM_DATA,
    Capability.INSERT_PICTURE,
    Capability.SET_FONT,
    Capability.GET_PAGE_COUNT,
    Capability.GET_DOCUMENT_INFO,
    Capability.IS_EMPTY,
}


class CrossPlatformHwpxController(HwpControllerBase):
    def __init__(self):
        self._builder: Optional[HwpxBuilder] = None
        self._current_path: Optional[str] = None
        self._is_modified: bool = False

    @property
    def platform(self) -> Platform:
        return Platform.CROSS_PLATFORM

    @property
    def capabilities(self) -> Set[Capability]:
        return CROSS_PLATFORM_CAPABILITIES

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def has_document(self) -> bool:
        return self._builder is not None

    @property
    def builder(self) -> HwpxBuilder:
        if self._builder is None:
            raise HwpError("No document open")
        return self._builder

    def connect(self, visible: bool = True) -> bool:
        return True

    def disconnect(self) -> bool:
        self._builder = None
        self._current_path = None
        return True

    def create_document(self) -> bool:
        try:
            self._builder = HwpxBuilder()
            self._current_path = None
            self._is_modified = False
            logger.info("Created new HWPX document")
            return True
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return False

    def open_document(self, path: str) -> bool:
        raise NotSupportedError(
            "Opening existing documents is not supported on cross-platform. "
            "Use pyhwp for reading or Windows controller for full editing.",
            capability=Capability.OPEN_DOCUMENT,
            current_platform=self.platform,
        )

    def save_document(self, path: str = None) -> bool:
        self.require_document()
        save_path = path or self._current_path
        if not save_path:
            raise HwpError("No save path specified and document has never been saved")

        try:
            if not save_path.endswith(".hwpx"):
                save_path += ".hwpx"
            self._builder.save(save_path)
            self._current_path = save_path
            self._is_modified = False
            logger.info(f"Saved HWPX document to: {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return False

    def save_as(self, path: str, format: str = "hwpx") -> bool:
        if format != "hwpx":
            raise NotSupportedError(
                f"Cross-platform controller only supports HWPX format, not '{format}'",
                capability=Capability.SAVE_AS_HWP
                if format == "hwp"
                else Capability.SAVE_AS_PDF,
                current_platform=self.platform,
            )
        return self.save_document(path)

    def close_document(self, save: bool = False) -> bool:
        if save and self.has_document:
            if self._current_path:
                self.save_document()
        self._builder = None
        self._current_path = None
        self._is_modified = False
        return True

    def insert_text(self, text: str) -> bool:
        self.require_document()
        try:
            self._builder.add_text(text)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False

    def get_text(self) -> str:
        self.require_document()
        return self._builder.text_content

    def create_table(
        self, rows: int, cols: int, data: Optional[List[List[str]]] = None
    ) -> bool:
        self.require_document()
        try:
            self._builder.add_table(rows=rows, cols=cols, data=data)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            return False

    def set_font(self, font_name: str, size: int = None) -> bool:
        logger.warning("set_font is not fully supported in cross-platform mode")
        return True

    def get_page_count(self) -> int:
        if not self.has_document:
            return 0
        text = self._builder.text_content
        lines = text.count("\n") + 1
        return max(1, lines // 50)

    def get_document_info(self) -> DocumentInfo:
        if not self.has_document:
            return DocumentInfo()

        text_content = self._builder.text_content
        return DocumentInfo(
            path=self._current_path,
            title=None,
            page_count=self.get_page_count(),
            is_modified=self._is_modified,
            is_empty=len(text_content) == 0,
            format="hwpx",
        )

    def is_modified(self) -> bool:
        return self._is_modified

    def is_empty(self) -> bool:
        if not self.has_document:
            return True
        return len(self._builder.text_content) == 0

    def insert_picture(self, path: str, **kwargs) -> bool:
        self.require_document()
        if not os.path.exists(path):
            raise HwpError(f"Image file not found: {path}")

        try:
            with open(path, "rb") as f:
                image_data = f.read()

            width_mm = kwargs.get("width", 100)
            height_mm = kwargs.get("height", 60)
            filename = os.path.basename(path)

            success = self._builder.insert_image(
                image_data=image_data,
                filename=filename,
                width_mm=width_mm,
                height_mm=height_mm,
            )
            if success:
                self._is_modified = True
            return success
        except Exception as e:
            logger.error(f"Failed to insert picture: {e}")
            return False

    # === Extended Methods (cross-platform specific) ===

    def add_heading(self, text: str, level: int = 1) -> bool:
        self.require_document()
        try:
            self._builder.add_heading(text, level=level)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to add heading: {e}")
            return False

    def add_paragraph(self, text: str, style: str = "default") -> bool:
        self.require_document()
        try:
            self._builder.add_paragraph(text, style=style)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to add paragraph: {e}")
            return False

    def add_chart(self, chart_type: str, data: Dict[str, Any], title: str = "") -> bool:
        self.require_document()
        try:
            self._builder.add_chart(chart_type=chart_type, data=data, title=title)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to add chart: {e}")
            return False

    def add_equation(self, latex: str) -> bool:
        self.require_document()
        try:
            self._builder.add_equation(latex)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to add equation: {e}")
            return False

    def add_formula(self, command: str) -> bool:
        self.require_document()
        try:
            self._builder.add_formula(command)
            self._is_modified = True
            return True
        except Exception as e:
            logger.error(f"Failed to add formula: {e}")
            return False

    def insert_image_from_bytes(
        self, image_data: bytes, filename: str, width_mm: int = 100, height_mm: int = 60
    ) -> bool:
        self.require_document()
        try:
            success = self._builder.insert_image(
                image_data=image_data,
                filename=filename,
                width_mm=width_mm,
                height_mm=height_mm,
            )
            if success:
                self._is_modified = True
            return success
        except Exception as e:
            logger.error(f"Failed to insert image from bytes: {e}")
            return False
