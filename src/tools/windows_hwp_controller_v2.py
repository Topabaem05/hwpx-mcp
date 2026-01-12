"""
Windows HWP Controller V2 - Implements HwpControllerBase using pyhwpx COM automation.
Provides full access to ~219 pyhwpx methods through the unified interface.
"""

import sys
import os
import logging
from typing import Optional, List, Dict, Any, Set

from .hwp_controller_base import (
    HwpControllerBase,
    Platform,
    Capability,
    HwpError,
    ConnectionError,
    DocumentNotOpenError,
    DocumentInfo,
    Position,
    TableInfo,
)

logger = logging.getLogger("hwp-mcp.windows_controller_v2")

IS_WINDOWS = sys.platform == "win32"

# All capabilities supported by pyhwpx (Windows COM)
WINDOWS_CAPABILITIES: Set[Capability] = set(Capability)


class WindowsHwpControllerV2(HwpControllerBase):
    def __init__(self, visible: bool = True, register_security_module: bool = True):
        self._hwp = None
        self._visible = visible
        self._register_security_module = register_security_module
        self._is_connected = False
        self._has_document = False

        if not IS_WINDOWS:
            raise HwpError("WindowsHwpControllerV2 requires Windows platform")

    @property
    def platform(self) -> Platform:
        return Platform.WINDOWS

    @property
    def capabilities(self) -> Set[Capability]:
        return WINDOWS_CAPABILITIES

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._hwp is not None

    @property
    def has_document(self) -> bool:
        return self._has_document and self.is_connected

    @property
    def hwp(self):
        """Direct access to underlying pyhwpx object for advanced operations."""
        if not self.is_connected:
            raise ConnectionError("Not connected to HWP")
        return self._hwp

    def connect(self, visible: bool = True) -> bool:
        if self.is_connected:
            return True

        try:
            from pyhwpx import Hwp

            self._hwp = Hwp(visible=visible)
            self._visible = visible
            self._is_connected = True

            if self._register_security_module:
                self._try_register_security_module()

            logger.info("Connected to HWP via pyhwpx")
            return True

        except ImportError:
            logger.error("pyhwpx not installed")
            raise HwpError("pyhwpx is not installed. Install with: pip install pyhwpx")
        except Exception as e:
            logger.error(f"Failed to connect to HWP: {e}")
            raise ConnectionError(f"Failed to connect to HWP: {e}")

    def _try_register_security_module(self) -> None:
        try:
            module_paths = [
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "security_module",
                    "FilePathCheckerModuleExample.dll",
                ),
                "D:/hwp-mcp/security_module/FilePathCheckerModuleExample.dll",
            ]
            for path in module_paths:
                if os.path.exists(path):
                    self._hwp.Application.RegisterModule(
                        "FilePathCheckerModuleExample", path
                    )
                    logger.info(f"Security module registered: {path}")
                    return
            logger.debug("Security module not found")
        except Exception as e:
            logger.debug(f"Security module registration skipped: {e}")

    def disconnect(self) -> bool:
        if not self.is_connected:
            return True
        try:
            self._hwp.quit()
            self._hwp = None
            self._is_connected = False
            self._has_document = False
            logger.info("Disconnected from HWP")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False

    def create_document(self) -> bool:
        self.require_connection()
        try:
            self._hwp.add_doc()
            self._has_document = True
            return True
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return False

    def open_document(self, path: str) -> bool:
        self.require_connection()
        if not os.path.exists(path):
            raise HwpError(f"File not found: {path}")
        try:
            self._hwp.open(path)
            self._has_document = True
            return True
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            return False

    def save_document(self, path: str = None) -> bool:
        self.require_document()
        try:
            if path:
                self._hwp.save_as(path)
            else:
                self._hwp.save()
            return True
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return False

    def save_as(self, path: str, format: str = "hwpx") -> bool:
        self.require_document()
        try:
            format_map = {
                "hwp": "hwp",
                "hwpx": "hwpx",
                "pdf": "pdf",
                "doc": "doc",
                "docx": "docx",
                "txt": "txt",
                "html": "html",
            }
            self._hwp.save_as(path, format=format_map.get(format, format))
            return True
        except Exception as e:
            logger.error(f"Failed to save as {format}: {e}")
            return False

    def close_document(self, save: bool = False) -> bool:
        self.require_connection()
        try:
            if save:
                self._hwp.save()
            self._hwp.clear()
            self._has_document = False
            return True
        except Exception as e:
            logger.error(f"Failed to close document: {e}")
            return False

    def insert_text(self, text: str) -> bool:
        self.require_document()
        try:
            self._hwp.insert_text(text)
            return True
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False

    def get_text(self) -> str:
        self.require_document()
        try:
            return self._hwp.get_text()
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return ""

    def get_selected_text(self) -> str:
        self.require_document()
        try:
            return self._hwp.get_selected_text()
        except Exception as e:
            logger.error(f"Failed to get selected text: {e}")
            return ""

    def find(self, text: str, forward: bool = True) -> bool:
        self.require_document()
        try:
            if forward:
                return self._hwp.find_forward(text)
            else:
                return self._hwp.find_backward(text)
        except Exception as e:
            logger.error(f"Failed to find text: {e}")
            return False

    def find_replace(self, find_text: str, replace_text: str) -> bool:
        self.require_document()
        try:
            return self._hwp.find_replace(find_text, replace_text)
        except Exception as e:
            logger.error(f"Failed to find/replace: {e}")
            return False

    def find_replace_all(self, find_text: str, replace_text: str) -> int:
        self.require_document()
        try:
            return self._hwp.find_replace_all(find_text, replace_text)
        except Exception as e:
            logger.error(f"Failed to find/replace all: {e}")
            return 0

    def create_table(
        self, rows: int, cols: int, data: Optional[List[List[str]]] = None
    ) -> bool:
        self.require_document()
        try:
            self._hwp.create_table(rows=rows, cols=cols)
            if data:
                self._fill_table_data(data)
            return True
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            return False

    def _fill_table_data(self, data: List[List[str]]) -> None:
        for row_idx, row in enumerate(data):
            for col_idx, cell_value in enumerate(row):
                self._hwp.Run("TableSelCell")
                self._hwp.Run("Delete")
                self._hwp.insert_text(str(cell_value))
                if col_idx < len(row) - 1:
                    self._hwp.Run("TableRightCell")
            if row_idx < len(data) - 1:
                for _ in range(len(row) - 1):
                    self._hwp.Run("TableLeftCell")
                self._hwp.Run("TableLowerCell")

    def set_cell_text(self, row: int, col: int, text: str) -> bool:
        self.require_document()
        try:
            self._hwp.goto_cell(row, col)
            self._hwp.Run("TableSelCell")
            self._hwp.Run("Delete")
            self._hwp.insert_text(text)
            return True
        except Exception as e:
            logger.error(f"Failed to set cell text: {e}")
            return False

    def get_cell_text(self, row: int, col: int) -> str:
        self.require_document()
        try:
            self._hwp.goto_cell(row, col)
            self._hwp.Run("TableSelCell")
            return self._hwp.get_selected_text()
        except Exception as e:
            logger.error(f"Failed to get cell text: {e}")
            return ""

    def table_to_dataframe(self):
        self.require_document()
        try:
            return self._hwp.table_to_df()
        except Exception as e:
            logger.error(f"Failed to convert table to dataframe: {e}")
            return None

    def set_font(self, font_name: str, size: int = None) -> bool:
        self.require_document()
        try:
            self._hwp.set_font(font_name=font_name, font_size=size)
            return True
        except Exception as e:
            logger.error(f"Failed to set font: {e}")
            return False

    def set_charshape(self, **kwargs) -> bool:
        self.require_document()
        try:
            self._hwp.set_charshape(**kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to set charshape: {e}")
            return False

    def get_charshape(self) -> Dict[str, Any]:
        self.require_document()
        try:
            return self._hwp.get_charshape_as_dict()
        except Exception as e:
            logger.error(f"Failed to get charshape: {e}")
            return {}

    def set_parashape(self, **kwargs) -> bool:
        self.require_document()
        try:
            self._hwp.set_parashape(**kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to set parashape: {e}")
            return False

    def goto_page(self, page: int) -> bool:
        self.require_document()
        try:
            self._hwp.goto_page(page)
            return True
        except Exception as e:
            logger.error(f"Failed to goto page: {e}")
            return False

    def get_page_count(self) -> int:
        self.require_document()
        try:
            return self._hwp.PageCount
        except Exception as e:
            logger.error(f"Failed to get page count: {e}")
            return 0

    def get_current_page(self) -> int:
        self.require_document()
        try:
            return self._hwp.current_page
        except Exception as e:
            logger.error(f"Failed to get current page: {e}")
            return 0

    def create_field(self, name: str) -> bool:
        self.require_document()
        try:
            self._hwp.create_field(name)
            return True
        except Exception as e:
            logger.error(f"Failed to create field: {e}")
            return False

    def get_field_text(self, name: str) -> str:
        self.require_document()
        try:
            return self._hwp.get_field_text(name)
        except Exception as e:
            logger.error(f"Failed to get field text: {e}")
            return ""

    def put_field_text(self, name: str, text: str) -> bool:
        self.require_document()
        try:
            self._hwp.put_field_text(name, text)
            return True
        except Exception as e:
            logger.error(f"Failed to put field text: {e}")
            return False

    def insert_picture(self, path: str, **kwargs) -> bool:
        self.require_document()
        if not os.path.exists(path):
            raise HwpError(f"Image file not found: {path}")
        try:
            self._hwp.insert_picture(path, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to insert picture: {e}")
            return False

    def insert_memo(self, text: str) -> bool:
        self.require_document()
        try:
            self._hwp.insert_memo(text)
            return True
        except Exception as e:
            logger.error(f"Failed to insert memo: {e}")
            return False

    def get_pos(self) -> Position:
        self.require_document()
        try:
            pos = self._hwp.get_pos()
            return Position(list_id=pos[0], para_id=pos[1], char_index=pos[2])
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return Position()

    def set_pos(self, list_id: int, para_id: int, char_index: int) -> bool:
        self.require_document()
        try:
            self._hwp.set_pos(list_id, para_id, char_index)
            return True
        except Exception as e:
            logger.error(f"Failed to set position: {e}")
            return False

    def get_document_info(self) -> DocumentInfo:
        self.require_document()
        try:
            path = self._hwp.Path if hasattr(self._hwp, "Path") else None
            return DocumentInfo(
                path=path,
                title=self._hwp.Title if hasattr(self._hwp, "Title") else None,
                page_count=self.get_page_count(),
                is_modified=self._hwp.IsModified
                if hasattr(self._hwp, "IsModified")
                else False,
                is_empty=self._hwp.IsEmpty if hasattr(self._hwp, "IsEmpty") else True,
                format="hwp" if path and path.endswith(".hwp") else "hwpx",
            )
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return DocumentInfo()

    def is_modified(self) -> bool:
        if not self.has_document:
            return False
        try:
            return self._hwp.IsModified
        except Exception:
            return False

    def is_empty(self) -> bool:
        if not self.has_document:
            return True
        try:
            return self._hwp.IsEmpty
        except Exception:
            return True

    def set_visible(self, visible: bool) -> bool:
        self.require_connection()
        try:
            self._hwp.set_visible(visible)
            self._visible = visible
            return True
        except Exception as e:
            logger.error(f"Failed to set visible: {e}")
            return False

    # === Extended pyhwpx Methods (not in base class) ===

    def run_action(self, action_name: str) -> bool:
        """Run a HWP action by name (e.g., 'BreakPara', 'Copy', 'Paste')."""
        self.require_document()
        try:
            self._hwp.Run(action_name)
            return True
        except Exception as e:
            logger.error(f"Failed to run action '{action_name}': {e}")
            return False

    def break_paragraph(self) -> bool:
        """Insert paragraph break."""
        return self.run_action("BreakPara")

    def break_page(self) -> bool:
        """Insert page break."""
        return self.run_action("BreakPage")

    def break_section(self) -> bool:
        """Insert section break."""
        return self.run_action("BreakSection")

    def select_all(self) -> bool:
        """Select all content."""
        return self.run_action("SelectAll")

    def copy(self) -> bool:
        """Copy selection to clipboard."""
        return self.run_action("Copy")

    def paste(self) -> bool:
        """Paste from clipboard."""
        return self.run_action("Paste")

    def cut(self) -> bool:
        """Cut selection to clipboard."""
        return self.run_action("Cut")

    def undo(self) -> bool:
        """Undo last action."""
        return self.run_action("Undo")

    def redo(self) -> bool:
        """Redo last undone action."""
        return self.run_action("Redo")

    def get_field_list(self, option: int = 0) -> List[str]:
        """Get list of all fields in document."""
        self.require_document()
        try:
            field_str = self._hwp.get_field_list(option)
            return field_str.split("\r\n") if field_str else []
        except Exception as e:
            logger.error(f"Failed to get field list: {e}")
            return []

    def create_page_image(
        self, output_path: str, page_no: int = 0, resolution: int = 96, fmt: str = "png"
    ) -> bool:
        """Create image from document page."""
        self.require_document()
        try:
            return self._hwp.create_page_image(
                output_path, page_no, resolution, 24, fmt
            )
        except Exception as e:
            logger.error(f"Failed to create page image: {e}")
            return False

    def cell_fill(self, color: str) -> bool:
        """Fill selected cell with color."""
        self.require_document()
        try:
            self._hwp.cell_fill(color)
            return True
        except Exception as e:
            logger.error(f"Failed to fill cell: {e}")
            return False

    def get_table_info(self) -> Optional[TableInfo]:
        """Get info about current table."""
        self.require_document()
        try:
            ctrl = self._hwp.ParentCtrl
            if ctrl and ctrl.CtrlID == "tbl":
                props = ctrl.Properties
                return TableInfo(
                    rows=props.RowCount if hasattr(props, "RowCount") else 0,
                    cols=props.ColCount if hasattr(props, "ColCount") else 0,
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return None

    def export_to_pdf(self, output_path: str) -> bool:
        """Export document to PDF."""
        return self.save_as(output_path, format="pdf")

    def insert_hyperlink(self, url: str, text: str = None) -> bool:
        """Insert hyperlink at cursor."""
        self.require_document()
        try:
            self._hwp.insert_hyperlink(url, text or url)
            return True
        except Exception as e:
            logger.error(f"Failed to insert hyperlink: {e}")
            return False

    def set_linespacing(self, spacing: int, spacing_type: int = 0) -> bool:
        """Set line spacing for current paragraph."""
        self.require_document()
        try:
            self._hwp.set_linespacing(spacing, spacing_type)
            return True
        except Exception as e:
            logger.error(f"Failed to set line spacing: {e}")
            return False

    def table_from_dataframe(self, df, has_header: bool = True) -> bool:
        """Create table from pandas DataFrame."""
        self.require_document()
        try:
            self._hwp.table_from_df(df, has_header=has_header)
            return True
        except Exception as e:
            logger.error(f"Failed to create table from dataframe: {e}")
            return False

    def get_ctrl_list(self) -> List[Any]:
        """Get list of all controls in document."""
        self.require_document()
        try:
            return self._hwp.ctrl_list()
        except Exception as e:
            logger.error(f"Failed to get ctrl list: {e}")
            return []

    def delete_ctrl(self, ctrl) -> bool:
        """Delete a control from document."""
        self.require_document()
        try:
            self._hwp.delete_ctrl(ctrl)
            return True
        except Exception as e:
            logger.error(f"Failed to delete ctrl: {e}")
            return False

    def get_available_fonts(self) -> List[str]:
        """Get list of available fonts."""
        self.require_connection()
        try:
            return self._hwp.get_available_font()
        except Exception as e:
            logger.error(f"Failed to get available fonts: {e}")
            return []

    # === New High-Priority Methods from pyhwpx ===

    def get_charshape_as_dict(self) -> Dict[str, Any]:
        """Get current character shape as a readable dictionary."""
        self.require_connection()
        try:
            return self._hwp.get_charshape_as_dict()
        except Exception as e:
            logger.error(f"Failed to get charshape as dict: {e}")
            return {}

    def get_parashape_as_dict(self) -> Dict[str, Any]:
        """Get current paragraph shape as a readable dictionary."""
        self.require_connection()
        try:
            return self._hwp.get_parashape_as_dict()
        except Exception as e:
            logger.error(f"Failed to get parashape as dict: {e}")
            return {}

    def get_pagedef_as_dict(self) -> Dict[str, Any]:
        """Get current page definition as a readable dictionary (mm units)."""
        self.require_connection()
        try:
            return self._hwp.get_pagedef_as_dict()
        except Exception as e:
            logger.error(f"Failed to get pagedef as dict: {e}")
            return {}

    def get_page_text(self, page_no: int = 0, option: int = 0xFFFFFFFF) -> str:
        """Get text from a specific page.

        Args:
            page_no: Page number (0-based). 0 = first page.
            option: Extract options (0x00=normal, 0x01=table, 0x02=textbox, 0x04=caption)
        """
        self.require_connection()
        try:
            return self._hwp.get_page_text(page_no, option)
        except Exception as e:
            logger.error(f"Failed to get page text: {e}")
            return ""

    def get_cell_addr(self, as_str: bool = True):
        """Get current cell address.

        Args:
            as_str: If True, returns "A1" format. If False, returns (row, col) tuple.
        """
        self.require_connection()
        try:
            return self._hwp.get_cell_addr("str" if as_str else "tuple")
        except Exception as e:
            logger.error(f"Failed to get cell addr: {e}")
            return "" if as_str else (0, 0)

    def get_selected_pos(self) -> tuple:
        """Get selected block positions.

        Returns:
            Tuple of (is_block, slist, spara, spos, elist, epara, epos)
        """
        self.require_connection()
        try:
            return self._hwp.get_selected_pos()
        except Exception as e:
            logger.error(f"Failed to get selected pos: {e}")
            return (False, 0, 0, 0, 0, 0, 0)

    def adjust_cellwidth(self, width, as_type: str = "ratio") -> bool:
        """Adjust column widths in a table.

        Args:
            width: Single value or list of ratios/mm values
            as_type: "ratio" for proportional, "mm" for absolute millimeters
        """
        self.require_connection()
        try:
            return self._hwp.adjust_cellwidth(width, as_=as_type)
        except Exception as e:
            logger.error(f"Failed to adjust cellwidth: {e}")
            return False

    def compose_chars(
        self,
        chars: str,
        char_size: int = -3,
        check_compose: int = 0,
        circle_type: int = 0,
    ) -> bool:
        """Create composed/circled characters (원문자).

        Args:
            chars: Characters to compose
            char_size: Size (-3 = 100%, -8 = 50%, 2 = 150%)
            check_compose: Whether to overlap characters (0 = no overlap)
            circle_type: Border shape (0=none, 1=circle, 2=inverted circle, 3=square, etc.)
        """
        self.require_connection()
        try:
            return self._hwp.compose_chars(chars, char_size, check_compose, circle_type)
        except Exception as e:
            logger.error(f"Failed to compose chars: {e}")
            return False

    def export_style(self, sty_filepath: str) -> bool:
        """Export document styles to .sty file."""
        self.require_connection()
        try:
            return self._hwp.export_style(sty_filepath)
        except Exception as e:
            logger.error(f"Failed to export style: {e}")
            return False

    def import_style(self, sty_filepath: str) -> bool:
        """Import styles from .sty file."""
        self.require_connection()
        try:
            return self._hwp.import_style(sty_filepath)
        except Exception as e:
            logger.error(f"Failed to import style: {e}")
            return False

    def get_style(self) -> Dict[str, Any]:
        """Get current paragraph style information."""
        self.require_connection()
        try:
            return self._hwp.get_style()
        except Exception as e:
            logger.error(f"Failed to get style: {e}")
            return {}

    def get_style_dict(self, as_type: str = "list") -> Any:
        """Get all style definitions as dictionary/list."""
        self.require_connection()
        try:
            return self._hwp.get_style_dict(as_=as_type)
        except Exception as e:
            logger.error(f"Failed to get style dict: {e}")
            return [] if as_type == "list" else {}

    def goto_addr(
        self, addr: str = "A1", col: int = 0, select_cell: bool = False
    ) -> bool:
        """Go to a specific cell address in a table.

        Args:
            addr: Cell address like "A1" or row number if col is specified
            col: Column number (1-based) when addr is row number
            select_cell: Whether to select the cell after moving
        """
        self.require_connection()
        try:
            return self._hwp.goto_addr(addr, col, select_cell)
        except Exception as e:
            logger.error(f"Failed to goto addr: {e}")
            return False

    def toggle_bold(self) -> bool:
        """Toggle bold formatting on selection."""
        return self.run_action("CharShapeBold")

    def toggle_italic(self) -> bool:
        """Toggle italic formatting on selection."""
        return self.run_action("CharShapeItalic")

    def toggle_underline(self) -> bool:
        """Toggle underline formatting on selection."""
        return self.run_action("CharShapeUnderline")

    def toggle_strikethrough(self) -> bool:
        """Toggle strikethrough formatting on selection."""
        return self.run_action("CharShapeCenterline")

    def insert_header_footer(self) -> bool:
        """Open header/footer editing mode."""
        return self.run_action("HeaderFooterModify")

    def delete_header_footer(self) -> bool:
        """Delete current header/footer."""
        return self.run_action("HeaderFooterDelete")

    def insert_endnote(self) -> bool:
        """Insert an endnote at current position."""
        return self.run_action("InsertEndnote")

    def insert_footnote(self) -> bool:
        """Insert a footnote at current position."""
        return self.run_action("InsertFootnote")

    def insert_comment(self) -> bool:
        """Insert a hidden comment at current position."""
        return self.run_action("Comment")

    def delete_comment(self) -> bool:
        """Delete current hidden comment."""
        return self.run_action("CommentDelete")

    def break_column(self) -> bool:
        """Insert a column break (for multi-column layouts)."""
        return self.run_action("BreakColumn")

    def break_line(self) -> bool:
        """Insert a line break (Shift+Enter - keeps paragraph formatting)."""
        return self.run_action("BreakLine")

    def move_to_start(self) -> bool:
        """Move cursor to document start."""
        return self.run_action("MoveDocBegin")

    def move_to_end(self) -> bool:
        """Move cursor to document end."""
        return self.run_action("MoveDocEnd")

    def move_to_line_start(self) -> bool:
        """Move cursor to line start."""
        return self.run_action("MoveLineBegin")

    def move_to_line_end(self) -> bool:
        """Move cursor to line end."""
        return self.run_action("MoveLineEnd")

    def move_to_para_start(self) -> bool:
        """Move cursor to paragraph start."""
        return self.run_action("MoveParaBegin")

    def move_to_para_end(self) -> bool:
        """Move cursor to paragraph end."""
        return self.run_action("MoveParaEnd")

    def insert_form_checkbox(self) -> bool:
        """Insert a form checkbox object."""
        return self.run_action("FormObjCreatorCheckButton")

    def insert_form_combobox(self) -> bool:
        """Insert a form combobox object."""
        return self.run_action("FormObjCreatorComboBox")

    def insert_form_edit(self) -> bool:
        """Insert a form text edit object."""
        return self.run_action("FormObjCreatorEdit")

    def insert_form_listbox(self) -> bool:
        """Insert a form listbox object."""
        return self.run_action("FormObjCreatorListBox")

    def insert_form_radio(self) -> bool:
        """Insert a form radio button object."""
        return self.run_action("FormObjCreatorRadioButton")

    def insert_form_button(self) -> bool:
        """Insert a form push button object."""
        return self.run_action("FormObjCreatorPushButton")

    def get_linespacing(self, method: str = "Percent"):
        """Get current line spacing.

        Args:
            method: "Percent", "Fixed", "BetweenLines", or "AtLeast"
        """
        self.require_connection()
        try:
            return self._hwp.get_linespacing(method)
        except Exception as e:
            logger.error(f"Failed to get linespacing: {e}")
            return 0

    def find_advanced(
        self,
        src: str,
        direction: str = "Forward",
        regex: bool = False,
        match_case: bool = True,
    ) -> bool:
        """Advanced find with regex and direction support."""
        self.require_connection()
        try:
            return self._hwp.find(
                src, direction=direction, regex=regex, MatchCase=1 if match_case else 0
            )
        except Exception as e:
            logger.error(f"Failed to find_advanced: {e}")
            return False

    def find_replace_advanced(
        self,
        src: str,
        dst: str,
        regex: bool = False,
        direction: str = "Forward",
    ) -> bool:
        """Advanced find/replace with regex support."""
        self.require_connection()
        try:
            return self._hwp.find_replace(src, dst, regex=regex, direction=direction)
        except Exception as e:
            logger.error(f"Failed to find_replace_advanced: {e}")
            return False

    def find_replace_all_advanced(
        self,
        src: str,
        dst: str,
        regex: bool = False,
    ) -> int:
        """Advanced find/replace all with regex support. Returns count of replacements."""
        self.require_connection()
        try:
            return self._hwp.find_replace_all(src, dst, regex=regex)
        except Exception as e:
            logger.error(f"Failed to find_replace_all_advanced: {e}")
            return 0

    def get_text_file(self, format: str = "UNICODE", save_block: bool = True) -> str:
        """Get document or selection as text (clipboard-free alternative to Copy)."""
        self.require_connection()
        try:
            option = "saveblock:true" if save_block else ""
            return self._hwp.get_text_file(format, option)
        except Exception as e:
            logger.error(f"Failed to get_text_file: {e}")
            return ""

    def set_text_file(self, text: str, format: str = "UNICODE") -> bool:
        """Insert text content (clipboard-free alternative to Paste)."""
        self.require_connection()
        try:
            return self._hwp.set_text_file(text, format)
        except Exception as e:
            logger.error(f"Failed to set_text_file: {e}")
            return False

    def get_field_info(self) -> List[Dict[str, str]]:
        """Get info about all click-here fields (name, direction, memo)."""
        self.require_connection()
        try:
            return self._hwp.get_field_info()
        except Exception as e:
            logger.error(f"Failed to get_field_info: {e}")
            return []

    def field_exists(self, field_name: str) -> bool:
        """Check if a field with the given name exists."""
        self.require_connection()
        try:
            return self._hwp.field_exist(field_name)
        except Exception as e:
            logger.error(f"Failed to check field_exist: {e}")
            return False

    def get_table_width(self, as_unit: str = "mm") -> float:
        """Get current table width."""
        self.require_connection()
        try:
            return self._hwp.get_table_width(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_table_width: {e}")
            return 0.0

    def get_table_height(self, as_unit: str = "mm") -> float:
        """Get current table height."""
        self.require_connection()
        try:
            return self._hwp.get_table_height(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_table_height: {e}")
            return 0.0

    def get_row_height(self, as_unit: str = "mm") -> float:
        """Get current row height."""
        self.require_connection()
        try:
            return self._hwp.get_row_height(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_row_height: {e}")
            return 0.0

    def get_col_width(self, as_unit: str = "mm") -> float:
        """Get current column width."""
        self.require_connection()
        try:
            return self._hwp.get_col_width(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_col_width: {e}")
            return 0.0

    def get_table_outside_margin(self, as_unit: str = "mm") -> Dict[str, float]:
        """Get table outside margins (left, right, top, bottom)."""
        self.require_connection()
        try:
            return self._hwp.get_table_outside_margin(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_table_outside_margin: {e}")
            return {}

    def get_cell_margin(self, as_unit: str = "mm") -> Dict[str, float]:
        """Get cell inside margins (left, right, top, bottom)."""
        self.require_connection()
        try:
            return self._hwp.get_cell_margin(as_=as_unit)
        except Exception as e:
            logger.error(f"Failed to get_cell_margin: {e}")
            return {}

    def select_text(
        self, slist: int, spara: int, spos: int, elist: int, epara: int, epos: int
    ) -> bool:
        """Select a text range by position coordinates."""
        self.require_connection()
        try:
            return self._hwp.select_text((True, slist, spara, spos, elist, epara, epos))
        except Exception as e:
            logger.error(f"Failed to select_text: {e}")
            return False

    def get_into_table(self, table_index: int = 0) -> bool:
        """Move cursor into the Nth table (0-indexed)."""
        self.require_connection()
        try:
            return self._hwp.get_into_nth_table(table_index)
        except Exception as e:
            logger.error(f"Failed to get_into_table: {e}")
            return False

    def clear_document(self, option: int = 1) -> bool:
        """Clear document content. option: 0=ask, 1=discard (default), 2=save if dirty."""
        self.require_connection()
        try:
            self._hwp.clear(option)
            return True
        except Exception as e:
            logger.error(f"Failed to clear_document: {e}")
            return False

    def delete_field(self) -> bool:
        """Delete the click-here field at cursor (keeps content)."""
        return self.run_action("DeleteField")

    def cancel_selection(self) -> bool:
        """Cancel current selection (like pressing Esc)."""
        return self.run_action("Cancel")

    def close_list(self) -> bool:
        """Exit from current list context (table, text box, etc.) to parent."""
        return self.run_action("CloseEx")

    def move_next_para(self) -> bool:
        """Move to next paragraph."""
        return self.run_action("MoveNextPara")

    def move_prev_para(self) -> bool:
        """Move to previous paragraph."""
        return self.run_action("MovePrevPara")

    def move_next_word(self) -> bool:
        """Move to next word."""
        return self.run_action("MoveNextWord")

    def move_prev_word(self) -> bool:
        """Move to previous word."""
        return self.run_action("MovePrevWord")

    def select_para(self) -> bool:
        """Select entire current paragraph."""
        return self.run_action("SelectPara")

    def select_word(self) -> bool:
        """Select current word."""
        return self.run_action("SelectWord")

    def select_line(self) -> bool:
        """Select entire current line."""
        return self.run_action("SelectLine")

    def delete_word(self) -> bool:
        """Delete word at cursor (Ctrl+T)."""
        return self.run_action("DeleteWord")

    def delete_line(self) -> bool:
        """Delete entire line at cursor (Ctrl+Y)."""
        return self.run_action("DeleteLine")

    # === Header/Footer Operations ===

    def header_footer_modify(self) -> bool:
        """Enter header/footer edit mode."""
        return self.run_action("HeaderFooterModify")

    def header_footer_delete(self) -> bool:
        """Delete current header/footer."""
        return self.run_action("HeaderFooterDelete")

    # === Quick Bookmarks (0-9) ===

    def quick_mark_insert(self, index: int) -> bool:
        """Insert quick bookmark at current position (index 0-9)."""
        if not 0 <= index <= 9:
            raise ValueError("Quick mark index must be 0-9")
        return self.run_action(f"QuickMarkInsert{index}")

    def quick_mark_move(self, index: int) -> bool:
        """Move cursor to quick bookmark (index 0-9)."""
        if not 0 <= index <= 9:
            raise ValueError("Quick mark index must be 0-9")
        return self.run_action(f"QuickMarkMove{index}")

    # === Document/File Info ===

    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Get file info without opening (encryption status, version, format)."""
        self.require_connection()
        try:
            pset = self._hwp.get_file_info(filepath)
            return {
                "format": pset.Item("Format"),
                "version": pset.Item("VersionStr"),
                "encrypted": pset.Item("Encrypted"),
                "digest": pset.Item("Digest"),
            }
        except Exception as e:
            logger.error(f"Failed to get_file_info: {e}")
            return {}

    def get_font_list(self) -> List[str]:
        """Get list of fonts used in current document."""
        self.require_connection()
        try:
            return self._hwp.get_font_list()
        except Exception as e:
            logger.error(f"Failed to get_font_list: {e}")
            return []

    # === Control Manipulation ===

    def get_ctrl_by_ctrl_id(self, ctrl_id: str) -> list:
        """Get all controls by type ID (tbl, gso, pic, eqed, etc.)."""
        self.require_connection()
        try:
            return self._hwp.get_ctrl_by_ctrl_id(ctrl_id)
        except Exception as e:
            logger.error(f"Failed to get_ctrl_by_ctrl_id: {e}")
            return []

    def get_image_info(self, ctrl=None) -> Dict[str, Any]:
        """Get image information (name, original dimensions)."""
        self.require_connection()
        try:
            return self._hwp.get_image_info(ctrl)
        except Exception as e:
            logger.error(f"Failed to get_image_info: {e}")
            return {}

    # === Page Operations ===

    def copy_page(self) -> bool:
        """Copy entire current page."""
        return self.run_action("CopyPage")

    def paste_page(self) -> bool:
        """Paste copied page."""
        return self.run_action("PastePage")

    def delete_page(self) -> bool:
        """Delete current page."""
        return self.run_action("DeletePage")

    # === Tab/Window Management ===

    def add_tab(self) -> bool:
        """Add new document tab in current window."""
        self.require_connection()
        try:
            self._hwp.add_tab()
            return True
        except Exception as e:
            logger.error(f"Failed to add_tab: {e}")
            return False

    def switch_to_document(self, doc_index: int) -> bool:
        """Switch to document by index (0-based)."""
        self.require_connection()
        try:
            self._hwp.switch_to(doc_index)
            return True
        except Exception as e:
            logger.error(f"Failed to switch_to_document: {e}")
            return False

    # === Spell Check ===

    def auto_spell_run(self) -> bool:
        """Toggle automatic spell check on/off."""
        return self.run_action("AutoSpellRun")
