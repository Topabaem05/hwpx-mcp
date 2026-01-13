"""
HWP Controller Base - Platform-agnostic abstract base class for HWP document manipulation.
Provides unified interface for Windows (pyhwpx) and Cross-platform (python-hwpx) implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import platform
import logging

logger = logging.getLogger("hwp-mcp.controller")


class Platform(str, Enum):
    WINDOWS = "windows"
    CROSS_PLATFORM = "cross_platform"


class Capability(str, Enum):
    # Document Lifecycle
    CREATE_DOCUMENT = "create_document"
    OPEN_DOCUMENT = "open_document"
    SAVE_DOCUMENT = "save_document"
    SAVE_AS_HWP = "save_as_hwp"
    SAVE_AS_HWPX = "save_as_hwpx"
    SAVE_AS_PDF = "save_as_pdf"
    CLOSE_DOCUMENT = "close_document"
    QUIT = "quit"

    # Text Operations
    INSERT_TEXT = "insert_text"
    INSERT_TEXT_AT_CURSOR = "insert_text_at_cursor"
    GET_TEXT = "get_text"
    GET_SELECTED_TEXT = "get_selected_text"
    SELECT_TEXT = "select_text"
    FIND = "find"
    FIND_REPLACE = "find_replace"
    FIND_REPLACE_ALL = "find_replace_all"

    # Table Operations
    CREATE_TABLE = "create_table"
    TABLE_FROM_DATA = "table_from_data"
    TABLE_FROM_DATAFRAME = "table_from_dataframe"
    TABLE_TO_DATAFRAME = "table_to_dataframe"
    SET_CELL_TEXT = "set_cell_text"
    GET_CELL_TEXT = "get_cell_text"
    GET_TABLE_SIZE = "get_table_size"
    GET_TABLE_INFO = "get_table_info"
    SET_COLUMN_WIDTH = "set_column_width"
    SET_ROW_HEIGHT = "set_row_height"
    CELL_FILL = "cell_fill"

    # Formatting
    SET_FONT = "set_font"
    SET_CHARSHAPE = "set_charshape"
    GET_CHARSHAPE = "get_charshape"
    SET_PARASHAPE = "set_parashape"
    GET_PARASHAPE = "get_parashape"
    SET_STYLE = "set_style"
    GET_STYLE = "get_style"
    SET_LINESPACING = "set_linespacing"

    # Page & Layout
    GOTO_PAGE = "goto_page"
    GET_PAGE_COUNT = "get_page_count"
    GET_CURRENT_PAGE = "get_current_page"
    SET_PAGEDEF = "set_pagedef"
    GET_PAGEDEF = "get_pagedef"
    CREATE_PAGE_IMAGE = "create_page_image"

    # Fields & Metatags
    CREATE_FIELD = "create_field"
    GET_FIELD_TEXT = "get_field_text"
    PUT_FIELD_TEXT = "put_field_text"
    GET_FIELD_LIST = "get_field_list"
    RENAME_FIELD = "rename_field"

    # Controls & Objects
    INSERT_PICTURE = "insert_picture"
    INSERT_HYPERLINK = "insert_hyperlink"
    INSERT_MEMO = "insert_memo"
    DELETE_CTRL = "delete_ctrl"
    SELECT_CTRL = "select_ctrl"
    GET_CTRL_LIST = "get_ctrl_list"

    # Position & Selection
    GET_POS = "get_pos"
    SET_POS = "set_pos"
    MOVE_POS = "move_pos"
    SELECT_ALL = "select_all"
    COPY = "copy"
    PASTE = "paste"
    CUT = "cut"

    # Actions & Automation
    RUN_ACTION = "run_action"
    RUN_SCRIPT_MACRO = "run_script_macro"
    UNDO = "undo"
    REDO = "redo"
    BREAK_PARAGRAPH = "break_paragraph"
    BREAK_PAGE = "break_page"
    BREAK_SECTION = "break_section"

    # View & UI
    SET_VISIBLE = "set_visible"
    MAXIMIZE_WINDOW = "maximize_window"
    MINIMIZE_WINDOW = "minimize_window"

    # Utilities
    GET_DOCUMENT_INFO = "get_document_info"
    IS_MODIFIED = "is_modified"
    IS_EMPTY = "is_empty"
    GET_AVAILABLE_FONTS = "get_available_fonts"

    # Header/Footer
    HEADER_FOOTER_MODIFY = "header_footer_modify"
    HEADER_FOOTER_DELETE = "header_footer_delete"

    # Quick Bookmarks
    QUICK_MARK_INSERT = "quick_mark_insert"
    QUICK_MARK_MOVE = "quick_mark_move"

    # File Info
    GET_FILE_INFO = "get_file_info"
    GET_FONT_LIST = "get_font_list"

    # Control Manipulation
    GET_CTRL_BY_ID = "get_ctrl_by_id"
    GET_IMAGE_INFO = "get_image_info"

    # Page Operations
    COPY_PAGE = "copy_page"
    PASTE_PAGE = "paste_page"
    DELETE_PAGE = "delete_page"

    # Tab Management
    ADD_TAB = "add_tab"
    SWITCH_TO_DOCUMENT = "switch_to_document"

    # Spell Check
    AUTO_SPELL_RUN = "auto_spell_run"


class HwpError(Exception):
    pass


class NotSupportedError(HwpError):
    def __init__(
        self,
        message: str,
        capability: Capability = None,
        current_platform: Platform = None,
    ):
        self.capability = capability
        self.current_platform = current_platform
        super().__init__(message)


class ConnectionError(HwpError):
    pass


class DocumentNotOpenError(HwpError):
    pass


@dataclass
class DocumentInfo:
    path: Optional[str] = None
    title: Optional[str] = None
    page_count: int = 0
    is_modified: bool = False
    is_empty: bool = True
    format: str = "unknown"


@dataclass
class Position:
    list_id: int = 0
    para_id: int = 0
    char_index: int = 0


@dataclass
class TableInfo:
    rows: int = 0
    cols: int = 0
    width: int = 0
    height: int = 0


def get_current_platform() -> Platform:
    if platform.system() == "Windows":
        return Platform.WINDOWS
    return Platform.CROSS_PLATFORM


class HwpControllerBase(ABC):
    @property
    @abstractmethod
    def platform(self) -> Platform:
        pass

    @property
    @abstractmethod
    def capabilities(self) -> set:
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @property
    @abstractmethod
    def has_document(self) -> bool:
        pass

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def require_capability(self, capability: Capability) -> None:
        if not self.supports(capability):
            raise NotSupportedError(
                f"'{capability.value}' is not supported on {self.platform.value}",
                capability=capability,
                current_platform=self.platform,
            )

    def require_connection(self) -> None:
        if not self.is_connected:
            raise ConnectionError("Not connected to HWP")

    def require_document(self) -> None:
        if not self.has_document:
            raise DocumentNotOpenError("No document is open")

    # === Document Lifecycle ===
    @abstractmethod
    def connect(self, visible: bool = True) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        pass

    @abstractmethod
    def create_document(self) -> bool:
        pass

    @abstractmethod
    def open_document(self, path: str) -> bool:
        pass

    @abstractmethod
    def save_document(self, path: str = None) -> bool:
        pass

    @abstractmethod
    def save_as(self, path: str, format: str = "hwpx") -> bool:
        pass

    @abstractmethod
    def close_document(self, save: bool = False) -> bool:
        pass

    # === Text Operations ===
    @abstractmethod
    def insert_text(self, text: str) -> bool:
        pass

    @abstractmethod
    def get_text(self) -> str:
        pass

    def get_selected_text(self) -> str:
        self.require_capability(Capability.GET_SELECTED_TEXT)
        return ""

    def find(self, text: str, forward: bool = True) -> bool:
        self.require_capability(Capability.FIND)
        return False

    def find_replace(self, find_text: str, replace_text: str) -> bool:
        self.require_capability(Capability.FIND_REPLACE)
        return False

    def find_replace_all(self, find_text: str, replace_text: str) -> int:
        self.require_capability(Capability.FIND_REPLACE_ALL)
        return 0

    # === Table Operations ===
    @abstractmethod
    def create_table(
        self, rows: int, cols: int, data: Optional[List[List[str]]] = None
    ) -> bool:
        pass

    def set_cell_text(self, row: int, col: int, text: str) -> bool:
        self.require_capability(Capability.SET_CELL_TEXT)
        return False

    def get_cell_text(self, row: int, col: int) -> str:
        self.require_capability(Capability.GET_CELL_TEXT)
        return ""

    def table_to_dataframe(self):
        self.require_capability(Capability.TABLE_TO_DATAFRAME)
        return None

    # === Formatting ===
    def set_font(self, font_name: str, size: int = None) -> bool:
        self.require_capability(Capability.SET_FONT)
        return False

    def set_charshape(self, **kwargs) -> bool:
        self.require_capability(Capability.SET_CHARSHAPE)
        return False

    def get_charshape(self) -> Dict[str, Any]:
        self.require_capability(Capability.GET_CHARSHAPE)
        return {}

    def set_parashape(self, **kwargs) -> bool:
        self.require_capability(Capability.SET_PARASHAPE)
        return False

    # === Page & Layout ===
    def goto_page(self, page: int) -> bool:
        self.require_capability(Capability.GOTO_PAGE)
        return False

    @abstractmethod
    def get_page_count(self) -> int:
        pass

    def get_current_page(self) -> int:
        self.require_capability(Capability.GET_CURRENT_PAGE)
        return 0

    # === Fields ===
    def create_field(self, name: str) -> bool:
        self.require_capability(Capability.CREATE_FIELD)
        return False

    def get_field_text(self, name: str) -> str:
        self.require_capability(Capability.GET_FIELD_TEXT)
        return ""

    def put_field_text(self, name: str, text: str) -> bool:
        self.require_capability(Capability.PUT_FIELD_TEXT)
        return False

    # === Controls ===
    def insert_picture(self, path: str, **kwargs) -> bool:
        self.require_capability(Capability.INSERT_PICTURE)
        return False

    def insert_memo(self, text: str) -> bool:
        self.require_capability(Capability.INSERT_MEMO)
        return False

    # === Position ===
    def get_pos(self) -> Position:
        self.require_capability(Capability.GET_POS)
        return Position()

    def set_pos(self, list_id: int, para_id: int, char_index: int) -> bool:
        self.require_capability(Capability.SET_POS)
        return False

    # === Info ===
    @abstractmethod
    def get_document_info(self) -> DocumentInfo:
        pass

    def is_modified(self) -> bool:
        return False

    def is_empty(self) -> bool:
        return True

    # === View ===
    def set_visible(self, visible: bool) -> bool:
        self.require_capability(Capability.SET_VISIBLE)
        return False
