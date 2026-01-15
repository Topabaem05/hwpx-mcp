"""
Unified HWP Tools - Platform-aware MCP tool registration using the unified controller interface.
Exposes all HWP capabilities through a consistent API that works across platforms.
"""

import logging
import os
from typing import Optional, List, Dict, Any

from .controller_factory import (
    get_controller,
    reset_controller,
    get_platform_info,
    check_capability,
    get_capability_matrix,
)
from .hwp_controller_base import (
    HwpControllerBase,
    Capability,
    Platform,
    HwpError,
    NotSupportedError,
    DocumentInfo,
)

logger = logging.getLogger("hwp-mcp.unified_tools")


def _get_controller() -> HwpControllerBase:
    controller = get_controller()
    if not controller.is_connected:
        controller.connect()
    return controller


def _ensure_document() -> HwpControllerBase:
    controller = _get_controller()
    if not controller.has_document:
        controller.create_document()
    return controller


def register_unified_tools(mcp) -> None:
    @mcp.tool()
    def hwp_platform_info() -> dict:
        """Get current platform information and available HWP capabilities."""
        return get_platform_info()

    @mcp.tool()
    def hwp_capabilities() -> dict:
        """Get the full capability matrix showing what's supported on each platform."""
        return {
            "matrix": get_capability_matrix(),
            "current_platform": get_platform_info(),
        }

    @mcp.tool()
    def hwp_connect(visible: bool = True) -> dict:
        """Connect to HWP controller (auto-selects Windows COM or cross-platform)."""
        try:
            controller = get_controller()
            success = controller.connect(visible=visible)
            return {
                "success": success,
                "platform": controller.platform.value,
                "message": f"Connected via {controller.platform.value}",
            }
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_disconnect() -> dict:
        """Disconnect from HWP controller and release resources."""
        try:
            reset_controller()
            return {"success": True, "message": "Disconnected"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_create() -> dict:
        """Create a new HWP document."""
        try:
            controller = _get_controller()
            success = controller.create_document()
            return {
                "success": success,
                "message": "Document created"
                if success
                else "Failed to create document",
                "format": "hwp" if controller.platform == Platform.WINDOWS else "hwpx",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_open(path: str) -> dict:
        """Open an existing HWP/HWPX document."""
        try:
            controller = _get_controller()
            success = controller.open_document(path)
            return {
                "success": success,
                "message": f"Opened: {path}" if success else "Failed to open",
            }
        except NotSupportedError as e:
            return {"success": False, "message": str(e), "not_supported": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_save(path: Optional[str] = None) -> dict:
        """Save the current document."""
        try:
            controller = _ensure_document()
            success = controller.save_document(path)
            return {
                "success": success,
                "message": f"Saved to: {path}" if success else "Failed to save",
                "path": path,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_save_as(path: str, format: str = "hwpx") -> dict:
        """Save document in specified format (hwp, hwpx, pdf, etc.)."""
        try:
            controller = _ensure_document()
            success = controller.save_as(path, format=format)
            return {
                "success": success,
                "message": f"Saved as {format}: {path}"
                if success
                else f"Failed to save as {format}",
                "path": path,
                "format": format,
            }
        except NotSupportedError as e:
            return {"success": False, "message": str(e), "not_supported": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_close(save: bool = False) -> dict:
        """Close the current document."""
        try:
            controller = _get_controller()
            success = controller.close_document(save=save)
            return {"success": success, "message": "Document closed"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_text(text: str) -> dict:
        """Insert text at current cursor position."""
        try:
            controller = _ensure_document()
            success = controller.insert_text(text)
            preview = text[:50] + "..." if len(text) > 50 else text
            return {
                "success": success,
                "message": f"Inserted: {preview}"
                if success
                else "Failed to insert text",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_text() -> dict:
        """Get all text from the current document."""
        try:
            controller = _ensure_document()
            text = controller.get_text()
            return {
                "success": True,
                "text": text,
                "length": len(text),
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_find(text: str, forward: bool = True) -> dict:
        """Find text in the document."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.FIND):
                return {
                    "success": False,
                    "message": "Find not supported on this platform",
                }
            found = controller.find(text, forward=forward)
            return {
                "success": True,
                "found": found,
                "message": f"Found: {text}" if found else f"Not found: {text}",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_find_replace(find_text: str, replace_text: str) -> dict:
        """Find and replace text once."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.FIND_REPLACE):
                return {
                    "success": False,
                    "message": "Find/replace not supported on this platform",
                }
            success = controller.find_replace(find_text, replace_text)
            return {
                "success": success,
                "message": f"Replaced '{find_text}' with '{replace_text}'"
                if success
                else "Text not found",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_find_replace_all(find_text: str, replace_text: str) -> dict:
        """Find and replace all occurrences."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.FIND_REPLACE_ALL):
                return {
                    "success": False,
                    "message": "Find/replace all not supported on this platform",
                }
            count = controller.find_replace_all(find_text, replace_text)
            return {
                "success": count > 0,
                "count": count,
                "message": f"Replaced {count} occurrences",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_create_table(
        rows: int, cols: int, data: Optional[List[List[str]]] = None
    ) -> dict:
        """Create a table with optional data."""
        try:
            controller = _ensure_document()
            success = controller.create_table(rows=rows, cols=cols, data=data)
            return {
                "success": success,
                "message": f"Created {rows}x{cols} table"
                if success
                else "Failed to create table",
                "rows": rows,
                "cols": cols,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_font(font_name: str, size: Optional[int] = None) -> dict:
        """Set font for current selection or subsequent text."""
        try:
            controller = _ensure_document()
            success = controller.set_font(font_name=font_name, size=size)
            return {
                "success": success,
                "message": f"Font set to {font_name}"
                + (f" size {size}" if size else ""),
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_page_count() -> dict:
        """Get the total page count of the current document."""
        try:
            controller = _ensure_document()
            count = controller.get_page_count()
            return {"success": True, "page_count": count}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_goto_page(page: int) -> dict:
        """Navigate to a specific page."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GOTO_PAGE):
                return {
                    "success": False,
                    "message": "Goto page not supported on this platform",
                }
            success = controller.goto_page(page)
            return {
                "success": success,
                "message": f"Moved to page {page}"
                if success
                else f"Failed to go to page {page}",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_document_info() -> dict:
        """Get information about the current document."""
        try:
            controller = _ensure_document()
            info = controller.get_document_info()
            return {
                "success": True,
                "info": {
                    "path": info.path,
                    "title": info.title,
                    "page_count": info.page_count,
                    "is_modified": info.is_modified,
                    "is_empty": info.is_empty,
                    "format": info.format,
                },
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_picture(path: str, width: int = 0, height: int = 0) -> dict:
        """Insert an image at current cursor position."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.INSERT_PICTURE):
                return {
                    "success": False,
                    "message": "Insert picture not supported on this platform",
                }
            success = controller.insert_picture(path, width=width, height=height)
            return {
                "success": success,
                "message": f"Inserted image: {path}"
                if success
                else "Failed to insert image",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_create_field(name: str) -> dict:
        """Create a field (click-here block) at current position."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.CREATE_FIELD):
                return {
                    "success": False,
                    "message": "Create field not supported on this platform",
                }
            success = controller.create_field(name)
            return {
                "success": success,
                "message": f"Created field: {name}"
                if success
                else "Failed to create field",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_field_text(name: str) -> dict:
        """Get text from a named field."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_FIELD_TEXT):
                return {
                    "success": False,
                    "message": "Get field text not supported on this platform",
                }
            text = controller.get_field_text(name)
            return {"success": True, "field": name, "text": text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_put_field_text(name: str, text: str) -> dict:
        """Put text into a named field."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.PUT_FIELD_TEXT):
                return {
                    "success": False,
                    "message": "Put field text not supported on this platform",
                }
            success = controller.put_field_text(name, text)
            return {
                "success": success,
                "message": f"Set field '{name}' to '{text[:30]}...'"
                if success
                else "Failed",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_run_action(action_name: str) -> dict:
        """Run a HWP action by name (Windows only). Examples: BreakPara, Copy, Paste, Undo."""
        try:
            controller = _get_controller()
            if controller.platform != Platform.WINDOWS:
                return {
                    "success": False,
                    "message": "run_action only available on Windows",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.run_action(action_name)
                return {
                    "success": success,
                    "message": f"Executed action: {action_name}"
                    if success
                    else f"Failed: {action_name}",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_export_pdf(output_path: str) -> dict:
        """Export the current document to PDF."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SAVE_AS_PDF):
                return {
                    "success": False,
                    "message": "PDF export not supported on this platform",
                }
            success = controller.save_as(output_path, format="pdf")
            return {
                "success": success,
                "message": f"Exported to PDF: {output_path}"
                if success
                else "Failed to export PDF",
                "path": output_path,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_create_page_image(
        output_path: str, page_no: int = 0, resolution: int = 96
    ) -> dict:
        """Create an image from a document page (Windows only)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.CREATE_PAGE_IMAGE):
                return {
                    "success": False,
                    "message": "Page image not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.create_page_image(output_path, page_no, resolution)
                return {
                    "success": success,
                    "message": f"Created page image: {output_path}"
                    if success
                    else "Failed",
                    "path": output_path,
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_charshape() -> dict:
        """Get current character shape (formatting) settings."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_CHARSHAPE):
                return {
                    "success": False,
                    "message": "Get charshape not supported on this platform",
                }
            shape = controller.get_charshape()
            return {"success": True, "charshape": shape}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_charshape(
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        color: Optional[str] = None,
    ) -> dict:
        """Set character shape (formatting) for selection or subsequent text."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SET_CHARSHAPE):
                return {
                    "success": False,
                    "message": "Set charshape not supported on this platform",
                }

            kwargs = {}
            if font_name is not None:
                kwargs["font_name"] = font_name
            if font_size is not None:
                kwargs["font_size"] = font_size
            if bold is not None:
                kwargs["bold"] = bold
            if italic is not None:
                kwargs["italic"] = italic
            if underline is not None:
                kwargs["underline"] = underline
            if color is not None:
                kwargs["color"] = color

            success = controller.set_charshape(**kwargs)
            return {
                "success": success,
                "message": "Character shape set"
                if success
                else "Failed to set charshape",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Selection & Clipboard ===

    @mcp.tool()
    def hwp_get_selected_text() -> dict:
        """Get currently selected text in the document."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_SELECTED_TEXT):
                return {
                    "success": False,
                    "message": "Get selected text not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                text = controller.get_selected_text()
                return {"success": True, "text": text, "length": len(text)}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_select_all() -> dict:
        """Select all content in the document."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SELECT_ALL):
                return {
                    "success": False,
                    "message": "Select all not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.select_all()
                return {
                    "success": success,
                    "message": "Selected all" if success else "Failed to select all",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_copy() -> dict:
        """Copy selected content to clipboard."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.COPY):
                return {
                    "success": False,
                    "message": "Copy not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.copy()
                return {
                    "success": success,
                    "message": "Copied" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_paste() -> dict:
        """Paste clipboard content at current position."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.PASTE):
                return {
                    "success": False,
                    "message": "Paste not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.paste()
                return {
                    "success": success,
                    "message": "Pasted" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_cut() -> dict:
        """Cut selected content to clipboard."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.CUT):
                return {
                    "success": False,
                    "message": "Cut not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.cut()
                return {"success": success, "message": "Cut" if success else "Failed"}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Editing (Undo/Redo) ===

    @mcp.tool()
    def hwp_undo() -> dict:
        """Undo the last action."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.UNDO):
                return {
                    "success": False,
                    "message": "Undo not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.undo()
                return {
                    "success": success,
                    "message": "Undone" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_redo() -> dict:
        """Redo the last undone action."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.REDO):
                return {
                    "success": False,
                    "message": "Redo not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.redo()
                return {
                    "success": success,
                    "message": "Redone" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Paragraph & Page Breaks ===

    @mcp.tool()
    def hwp_break_paragraph() -> dict:
        """Insert a paragraph break (new line within same paragraph style)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.BREAK_PARAGRAPH):
                return {
                    "success": False,
                    "message": "Break paragraph not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.break_paragraph()
                return {
                    "success": success,
                    "message": "Paragraph break inserted" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_break_page() -> dict:
        """Insert a page break."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.BREAK_PAGE):
                return {
                    "success": False,
                    "message": "Break page not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.break_page()
                return {
                    "success": success,
                    "message": "Page break inserted" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_break_section() -> dict:
        """Insert a section break."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.BREAK_SECTION):
                return {
                    "success": False,
                    "message": "Break section not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.break_section()
                return {
                    "success": success,
                    "message": "Section break inserted" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Table Cell Operations ===

    @mcp.tool()
    def hwp_set_cell_text(row: int, col: int, text: str) -> dict:
        """Set text in a specific table cell (0-indexed)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SET_CELL_TEXT):
                return {
                    "success": False,
                    "message": "Set cell text not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.set_cell_text(row, col, text)
                return {
                    "success": success,
                    "message": f"Set cell ({row},{col})" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_cell_text(row: int, col: int) -> dict:
        """Get text from a specific table cell (0-indexed)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_CELL_TEXT):
                return {
                    "success": False,
                    "message": "Get cell text not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                text = controller.get_cell_text(row, col)
                return {"success": True, "row": row, "col": col, "text": text}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_cell_fill(color: str) -> dict:
        """Fill the current cell with a color (e.g., '#FF0000' for red)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.CELL_FILL):
                return {
                    "success": False,
                    "message": "Cell fill not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.cell_fill(color)
                return {
                    "success": success,
                    "message": f"Cell filled with {color}" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_table_info() -> dict:
        """Get information about the currently selected table."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_TABLE_INFO):
                return {
                    "success": False,
                    "message": "Get table info not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                info = controller.get_table_info()
                if info:
                    return {
                        "success": True,
                        "info": {
                            "rows": info.rows,
                            "cols": info.cols,
                            "width": info.width,
                            "height": info.height,
                        },
                    }
                return {"success": False, "message": "No table selected"}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Paragraph Formatting ===

    @mcp.tool()
    def hwp_set_parashape(
        alignment: Optional[str] = None,
        line_spacing: Optional[int] = None,
        indent_left: Optional[int] = None,
        indent_right: Optional[int] = None,
        margin_top: Optional[int] = None,
        margin_bottom: Optional[int] = None,
    ) -> dict:
        """Set paragraph formatting. alignment: 'left', 'center', 'right', 'justify'."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SET_PARASHAPE):
                return {
                    "success": False,
                    "message": "Set parashape not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                kwargs = {}
                if alignment is not None:
                    kwargs["alignment"] = alignment
                if line_spacing is not None:
                    kwargs["line_spacing"] = line_spacing
                if indent_left is not None:
                    kwargs["indent_left"] = indent_left
                if indent_right is not None:
                    kwargs["indent_right"] = indent_right
                if margin_top is not None:
                    kwargs["margin_top"] = margin_top
                if margin_bottom is not None:
                    kwargs["margin_bottom"] = margin_bottom

                success = controller.set_parashape(**kwargs)
                return {
                    "success": success,
                    "message": "Paragraph shape set" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_linespacing(spacing: int, spacing_type: int = 0) -> dict:
        """Set line spacing. spacing_type: 0=percent, 1=fixed(pt), 2=ratio."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SET_LINESPACING):
                return {
                    "success": False,
                    "message": "Set line spacing not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.set_linespacing(spacing, spacing_type)
                return {
                    "success": success,
                    "message": f"Line spacing set to {spacing}"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Position & Navigation ===

    @mcp.tool()
    def hwp_get_current_page() -> dict:
        """Get the current page number (1-indexed)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_CURRENT_PAGE):
                return {
                    "success": False,
                    "message": "Get current page not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                page = controller.get_current_page()
                return {"success": True, "page": page}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_pos() -> dict:
        """Get current cursor position (list_id, para_id, char_index)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_POS):
                return {
                    "success": False,
                    "message": "Get position not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                pos = controller.get_pos()
                return {
                    "success": True,
                    "position": {
                        "list_id": pos.list_id,
                        "para_id": pos.para_id,
                        "char_index": pos.char_index,
                    },
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_pos(list_id: int, para_id: int, char_index: int) -> dict:
        """Set cursor position to specific location."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.SET_POS):
                return {
                    "success": False,
                    "message": "Set position not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.set_pos(list_id, para_id, char_index)
                return {
                    "success": success,
                    "message": f"Position set to ({list_id},{para_id},{char_index})"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Fields ===

    @mcp.tool()
    def hwp_get_field_list(option: int = 0) -> dict:
        """Get list of all field names in the document. option: 0=all, 1=clickhere only."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_FIELD_LIST):
                return {
                    "success": False,
                    "message": "Get field list not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                fields = controller.get_field_list(option)
                return {"success": True, "fields": fields, "count": len(fields)}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Utilities ===

    @mcp.tool()
    def hwp_insert_hyperlink(url: str, text: Optional[str] = None) -> dict:
        """Insert a hyperlink at current position."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.INSERT_HYPERLINK):
                return {
                    "success": False,
                    "message": "Insert hyperlink not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_hyperlink(url, text)
                return {
                    "success": success,
                    "message": f"Hyperlink inserted: {url}" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_memo(text: str) -> dict:
        """Insert a memo (comment) at current position."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.INSERT_MEMO):
                return {
                    "success": False,
                    "message": "Insert memo not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_memo(text)
                return {
                    "success": success,
                    "message": f"Memo inserted" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_available_fonts() -> dict:
        """Get list of available fonts on the system."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_AVAILABLE_FONTS):
                return {
                    "success": False,
                    "message": "Get fonts not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                fonts = controller.get_available_fonts()
                return {"success": True, "fonts": fonts, "count": len(fonts)}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_visible(visible: bool) -> dict:
        """Show or hide the HWP application window."""
        try:
            controller = _get_controller()
            if not check_capability(Capability.SET_VISIBLE):
                return {
                    "success": False,
                    "message": "Set visible not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.set_visible(visible)
                return {
                    "success": success,
                    "message": f"Visibility set to {visible}" if success else "Failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === DataFrame Integration ===

    @mcp.tool()
    def hwp_table_from_dataframe(
        data: List[List[Any]], columns: List[str], has_header: bool = True
    ) -> dict:
        """Create a table from tabular data (simulating DataFrame). Columns are header names, data is list of rows."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.TABLE_FROM_DATAFRAME):
                return {
                    "success": False,
                    "message": "Table from DataFrame not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                try:
                    import pandas as pd

                    df = pd.DataFrame(data, columns=columns)
                    success = controller.table_from_dataframe(df, has_header=has_header)
                    return {
                        "success": success,
                        "message": f"Created {len(df)}x{len(df.columns)} table"
                        if success
                        else "Failed",
                        "rows": len(df),
                        "cols": len(df.columns),
                    }
                except ImportError:
                    return {"success": False, "message": "pandas not installed"}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_table_to_dataframe() -> dict:
        """Extract current table as tabular data (rows and columns)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.TABLE_TO_DATAFRAME):
                return {
                    "success": False,
                    "message": "Table to DataFrame not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                df = controller.table_to_dataframe()
                if df is not None:
                    return {
                        "success": True,
                        "columns": list(df.columns),
                        "data": df.values.tolist(),
                        "rows": len(df),
                        "cols": len(df.columns),
                    }
                return {
                    "success": False,
                    "message": "No table found or extraction failed",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Control Operations ===

    @mcp.tool()
    def hwp_get_ctrl_list() -> dict:
        """Get list of all controls (objects) in the document."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.GET_CTRL_LIST):
                return {
                    "success": False,
                    "message": "Get control list not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                ctrls = controller.get_ctrl_list()
                ctrl_info = []
                for ctrl in ctrls:
                    try:
                        ctrl_info.append(
                            {
                                "ctrl_id": getattr(ctrl, "CtrlID", "unknown"),
                                "user_desc": getattr(ctrl, "UserDesc", ""),
                            }
                        )
                    except Exception:
                        ctrl_info.append({"ctrl_id": "unknown"})
                return {"success": True, "controls": ctrl_info, "count": len(ctrls)}
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_delete_ctrl(ctrl_index: int) -> dict:
        """Delete a control by index (from hwp_get_ctrl_list)."""
        try:
            controller = _ensure_document()
            if not check_capability(Capability.DELETE_CTRL):
                return {
                    "success": False,
                    "message": "Delete control not supported on this platform",
                }

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                ctrls = controller.get_ctrl_list()
                if 0 <= ctrl_index < len(ctrls):
                    success = controller.delete_ctrl(ctrls[ctrl_index])
                    return {
                        "success": success,
                        "message": f"Deleted control at index {ctrl_index}"
                        if success
                        else "Failed",
                    }
                return {
                    "success": False,
                    "message": f"Invalid index {ctrl_index}. Valid: 0-{len(ctrls) - 1}",
                }
            return {"success": False, "message": "Only available on Windows"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === ParamHelpers (pyhwpx parameter conversion utilities) ===

    @mcp.tool()
    def hwp_get_head_types() -> dict:
        """Get available paragraph heading types for outline/numbering."""
        return {
            "head_types": {
                "None": {"value": 0, "description": "없음 (보통 문단)"},
                "Outline": {"value": 1, "description": "개요 문단"},
                "Number": {"value": 2, "description": "번호 문단"},
                "Bullet": {"value": 3, "description": "글머리표 문단"},
            }
        }

    @mcp.tool()
    def hwp_get_line_types() -> dict:
        """Get available line types for tables and objects."""
        return {
            "line_types": {
                "None": {"value": 0, "description": "없음"},
                "Solid": {"value": 1, "description": "실선"},
                "Dash": {"value": 2, "description": "파선"},
                "Dot": {"value": 3, "description": "점선"},
                "DashDot": {"value": 4, "description": "일점쇄선"},
                "DashDotDot": {"value": 5, "description": "이점쇄선"},
                "LongDash": {"value": 6, "description": "긴 파선"},
                "Circle": {"value": 7, "description": "원형 점선"},
                "DoubleSlim": {"value": 8, "description": "이중 실선"},
                "SlimThick": {"value": 9, "description": "얇고 굵은 이중선"},
                "ThickSlim": {"value": 10, "description": "굵고 얇은 이중선"},
                "SlimThickSlim": {"value": 11, "description": "얇고 굵고 얇은 삼중선"},
            }
        }

    @mcp.tool()
    def hwp_get_line_widths() -> dict:
        """Get available line widths (0.1mm to 5.0mm)."""
        return {
            "line_widths": {
                "0.1mm": 0,
                "0.12mm": 1,
                "0.15mm": 2,
                "0.2mm": 3,
                "0.25mm": 4,
                "0.3mm": 5,
                "0.4mm": 6,
                "0.5mm": 7,
                "0.6mm": 8,
                "0.7mm": 9,
                "1.0mm": 10,
                "1.5mm": 11,
                "2.0mm": 12,
                "3.0mm": 13,
                "4.0mm": 14,
                "5.0mm": 15,
            }
        }

    @mcp.tool()
    def hwp_get_number_formats() -> dict:
        """Get available number formats for outline numbering."""
        return {
            "number_formats": {
                "Digit": {"value": 0, "example": "1, 2, 3"},
                "CircledDigit": {"value": 1, "example": "①, ②, ③"},
                "RomanCapital": {"value": 2, "example": "I, II, III"},
                "RomanSmall": {"value": 3, "example": "i, ii, iii"},
                "LatinCapital": {"value": 4, "example": "A, B, C"},
                "LatinSmall": {"value": 5, "example": "a, b, c"},
                "CircledLatinCapital": {"value": 6, "example": "Ⓐ, Ⓑ, Ⓒ"},
                "CircledLatinSmall": {"value": 7, "example": "ⓐ, ⓑ, ⓒ"},
                "HangulSyllable": {"value": 8, "example": "가, 나, 다"},
                "CircledHangulSyllable": {"value": 9, "example": "㉮, ㉯, ㉰"},
                "HangulJamo": {"value": 10, "example": "ㄱ, ㄴ, ㄷ"},
                "CircledHangulJamo": {"value": 11, "example": "㉠, ㉡, ㉢"},
                "HangulPhonetic": {"value": 12, "example": "일, 이, 삼"},
                "Ideograph": {"value": 13, "example": "一, 二, 三"},
                "CircledIdeograph": {"value": 14, "example": "㊀, ㊁, ㊂"},
                "DecagonCircle": {"value": 15, "example": "갑, 을, 병"},
                "DecagonCircleHanja": {"value": 16, "example": "甲, 乙, 丙"},
            }
        }

    @mcp.tool()
    def hwp_get_pic_effects() -> dict:
        """Get available picture effects."""
        return {
            "pic_effects": {
                "RealPic": {"value": 0, "description": "효과 없음 (원본)"},
                "GrayScale": {"value": 1, "description": "회색조"},
                "BlackWhite": {"value": 2, "description": "흑백"},
            }
        }

    @mcp.tool()
    def hwp_convert_unit(hwp_unit: int, to_mm: bool = True) -> dict:
        """Convert between HwpUnit and millimeters. HwpUnit = (mm * 7200 / 25.4)"""
        if to_mm:
            mm = round(hwp_unit / 7200 * 25.4, 2)
            return {
                "hwp_unit": hwp_unit,
                "mm": mm,
                "formula": "hwp_unit / 7200 * 25.4",
            }
        else:
            hwp_val = round(hwp_unit * 7200 / 25.4)
            return {
                "mm": hwp_unit,
                "hwp_unit": hwp_val,
                "formula": "mm * 7200 / 25.4",
            }

    @mcp.tool()
    def hwp_head_type(heading_type: str) -> dict:
        """Convert heading type string to HWP integer value."""
        types = {"None": 0, "Outline": 1, "Number": 2, "Bullet": 3}
        if heading_type not in types:
            return {
                "success": False,
                "message": f"Invalid type: {heading_type}. Valid: {list(types.keys())}",
            }
        return {"success": True, "type": heading_type, "value": types[heading_type]}

    @mcp.tool()
    def hwp_line_type(line_type: str = "Solid") -> dict:
        """Convert line type string to HWP integer value."""
        types = {
            "None": 0,
            "Solid": 1,
            "Dash": 2,
            "Dot": 3,
            "DashDot": 4,
            "DashDotDot": 5,
            "LongDash": 6,
            "Circle": 7,
            "DoubleSlim": 8,
            "SlimThick": 9,
            "ThickSlim": 10,
            "SlimThickSlim": 11,
        }
        if line_type not in types:
            return {
                "success": False,
                "message": f"Invalid type: {line_type}. Valid: {list(types.keys())}",
            }
        return {"success": True, "type": line_type, "value": types[line_type]}

    @mcp.tool()
    def hwp_line_width(width: str = "0.1mm") -> dict:
        """Convert line width string to HWP integer value."""
        widths = {
            "0.1mm": 0,
            "0.12mm": 1,
            "0.15mm": 2,
            "0.2mm": 3,
            "0.25mm": 4,
            "0.3mm": 5,
            "0.4mm": 6,
            "0.5mm": 7,
            "0.6mm": 8,
            "0.7mm": 9,
            "1.0mm": 10,
            "1.5mm": 11,
            "2.0mm": 12,
            "3.0mm": 13,
            "4.0mm": 14,
            "5.0mm": 15,
        }
        if width not in widths:
            return {
                "success": False,
                "message": f"Invalid width: {width}. Valid: {list(widths.keys())}",
            }
        return {"success": True, "width": width, "value": widths[width]}

    @mcp.tool()
    def hwp_number_format(num_format: str) -> dict:
        """Convert number format string to HWP integer value for outline numbering."""
        formats = {
            "Digit": 0,
            "CircledDigit": 1,
            "RomanCapital": 2,
            "RomanSmall": 3,
            "LatinCapital": 4,
            "LatinSmall": 5,
            "CircledLatinCapital": 6,
            "CircledLatinSmall": 7,
            "HangulSyllable": 8,
            "CircledHangulSyllable": 9,
            "HangulJamo": 10,
            "CircledHangulJamo": 11,
            "HangulPhonetic": 12,
            "Ideograph": 13,
            "CircledIdeograph": 14,
            "DecagonCircle": 15,
            "DecagonCircleHanja": 16,
        }
        if num_format not in formats:
            return {
                "success": False,
                "message": f"Invalid format: {num_format}. Valid: {list(formats.keys())}",
            }
        return {"success": True, "format": num_format, "value": formats[num_format]}

    @mcp.tool()
    def hwp_pic_effect(effect: str = "RealPic") -> dict:
        """Convert picture effect string to HWP integer value."""
        effects = {"RealPic": 0, "GrayScale": 1, "BlackWhite": 2}
        if effect not in effects:
            return {
                "success": False,
                "message": f"Invalid effect: {effect}. Valid: {list(effects.keys())}",
            }
        return {"success": True, "effect": effect, "value": effects[effect]}

    # === High-Priority New Tools (pyhwpx methods) ===

    @mcp.tool()
    def hwp_get_charshape_dict() -> dict:
        """Get current character shape as a readable dictionary with all formatting details."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                result = controller.get_charshape_as_dict()
                return {"success": True, "charshape": result}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_parashape_dict() -> dict:
        """Get current paragraph shape as a readable dictionary with all formatting details."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                result = controller.get_parashape_as_dict()
                return {"success": True, "parashape": result}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_pagedef_dict() -> dict:
        """Get current page definition (paper size, margins) as a dictionary in mm units."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                result = controller.get_pagedef_as_dict()
                return {"success": True, "pagedef": result}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_page_text(page_no: int = 0) -> dict:
        """Get text from a specific page (0-based index). Extracts all text including tables."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                text = controller.get_page_text(page_no)
                return {
                    "success": True,
                    "page": page_no,
                    "text": text,
                    "length": len(text),
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_cell_addr() -> dict:
        """Get current cell address in Excel-style format (e.g., 'A1'). Must be inside a table."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                addr = controller.get_cell_addr(as_str=True)
                if addr:
                    return {"success": True, "address": addr}
                return {"success": False, "message": "Not inside a table cell"}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_selected_pos() -> dict:
        """Get the start and end positions of the current selection/block."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                result = controller.get_selected_pos()
                return {
                    "success": True,
                    "is_block": result[0],
                    "start": {"list": result[1], "para": result[2], "pos": result[3]},
                    "end": {"list": result[4], "para": result[5], "pos": result[6]},
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_adjust_cellwidth(width: List[float], as_type: str = "ratio") -> dict:
        """Adjust column widths in a table. width=[1,2,3] sets columns to 1:2:3 ratio."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.adjust_cellwidth(width, as_type)
                return {
                    "success": success,
                    "message": f"Adjusted column widths to {width}"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_compose_chars(
        chars: str, circle_type: int = 1, char_size: int = -3
    ) -> dict:
        """Create circled characters (원문자). circle_type: 0=none, 1=circle, 3=square."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.compose_chars(chars, char_size, 0, circle_type)
                return {
                    "success": success,
                    "message": f"Created circled chars: {chars}"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_export_style(filepath: str) -> dict:
        """Export document styles to a .sty file."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.export_style(filepath)
                return {
                    "success": success,
                    "message": f"Exported styles to {filepath}"
                    if success
                    else "Failed",
                    "path": filepath,
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_import_style(filepath: str) -> dict:
        """Import styles from a .sty file."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.import_style(filepath)
                return {
                    "success": success,
                    "message": f"Imported styles from {filepath}"
                    if success
                    else "Failed",
                    "path": filepath,
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_style() -> dict:
        """Get current paragraph style information."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                result = controller.get_style()
                return {"success": True, "style": result}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_goto_cell(addr: str = "A1") -> dict:
        """Go to a specific cell address in a table (e.g., 'A1', 'B3')."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.goto_addr(addr)
                return {
                    "success": success,
                    "message": f"Moved to cell {addr}" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Quick Formatting Toggle Tools ===

    @mcp.tool()
    def hwp_toggle_bold() -> dict:
        """Toggle bold formatting on current selection."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.toggle_bold()
                return {
                    "success": success,
                    "message": "Toggled bold" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_toggle_italic() -> dict:
        """Toggle italic formatting on current selection."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.toggle_italic()
                return {
                    "success": success,
                    "message": "Toggled italic" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_toggle_underline() -> dict:
        """Toggle underline formatting on current selection."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.toggle_underline()
                return {
                    "success": success,
                    "message": "Toggled underline" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_toggle_strikethrough() -> dict:
        """Toggle strikethrough formatting on current selection."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.toggle_strikethrough()
                return {
                    "success": success,
                    "message": "Toggled strikethrough" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Document Structure Tools ===

    @mcp.tool()
    def hwp_insert_endnote() -> dict:
        """Insert an endnote at current cursor position."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_endnote()
                return {
                    "success": success,
                    "message": "Inserted endnote" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_footnote() -> dict:
        """Insert a footnote at current cursor position."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_footnote()
                return {
                    "success": success,
                    "message": "Inserted footnote" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_break_column() -> dict:
        """Insert a column break (for multi-column layouts)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.break_column()
                return {
                    "success": success,
                    "message": "Inserted column break" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_break_line() -> dict:
        """Insert a line break (Shift+Enter - keeps paragraph formatting)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.break_line()
                return {
                    "success": success,
                    "message": "Inserted line break" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Navigation Tools ===

    @mcp.tool()
    def hwp_move_to_start() -> dict:
        """Move cursor to document start."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.move_to_start()
                return {
                    "success": success,
                    "message": "Moved to start" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_move_to_end() -> dict:
        """Move cursor to document end."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.move_to_end()
                return {
                    "success": success,
                    "message": "Moved to end" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Form Object Tools ===

    @mcp.tool()
    def hwp_insert_form_checkbox() -> dict:
        """Insert a form checkbox object for interactive documents."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_form_checkbox()
                return {
                    "success": success,
                    "message": "Inserted checkbox" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_form_combobox() -> dict:
        """Insert a form combobox (dropdown) object for interactive documents."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_form_combobox()
                return {
                    "success": success,
                    "message": "Inserted combobox" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_form_edit() -> dict:
        """Insert a form text edit box for interactive documents."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_form_edit()
                return {
                    "success": success,
                    "message": "Inserted edit box" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_insert_form_radio() -> dict:
        """Insert a form radio button for interactive documents."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.insert_form_radio()
                return {
                    "success": success,
                    "message": "Inserted radio button" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_linespacing() -> dict:
        """Get current line spacing percentage."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                spacing = controller.get_linespacing()
                return {"success": True, "linespacing": spacing, "unit": "percent"}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Advanced Find & Replace ===

    @mcp.tool()
    def hwp_find_advanced(
        text: str,
        direction: str = "Forward",
        regex: bool = False,
        match_case: bool = True,
    ) -> dict:
        """Advanced find with regex and direction support. direction: 'Forward', 'Backward', 'All'."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                found = controller.find_advanced(
                    text, direction=direction, regex=regex, match_case=match_case
                )
                return {
                    "success": True,
                    "found": found,
                    "message": f"Found: {text}" if found else f"Not found: {text}",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_find_replace_advanced(
        find_text: str,
        replace_text: str,
        regex: bool = False,
        direction: str = "Forward",
    ) -> dict:
        """Advanced find/replace with regex support."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.find_replace_advanced(
                    find_text, replace_text, regex=regex, direction=direction
                )
                return {
                    "success": success,
                    "message": f"Replaced '{find_text}' with '{replace_text}'"
                    if success
                    else "Text not found",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_find_replace_all_advanced(
        find_text: str,
        replace_text: str,
        regex: bool = False,
    ) -> dict:
        """Advanced find/replace all with regex support. Returns count of replacements."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                count = controller.find_replace_all_advanced(
                    find_text, replace_text, regex=regex
                )
                return {
                    "success": count > 0,
                    "count": count,
                    "message": f"Replaced {count} occurrences",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Text File Operations (Clipboard-free) ===

    @mcp.tool()
    def hwp_get_text_file(format: str = "UNICODE", save_block: bool = True) -> dict:
        """Get document or selection as text (clipboard-free alternative to Copy)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                text = controller.get_text_file(format, save_block)
                return {
                    "success": True,
                    "text": text,
                    "length": len(text),
                    "format": format,
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_set_text_file(text: str, format: str = "UNICODE") -> dict:
        """Insert text content directly (clipboard-free alternative to Paste)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.set_text_file(text, format)
                return {
                    "success": success,
                    "message": "Inserted text" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Advanced Field Operations ===

    @mcp.tool()
    def hwp_get_field_info() -> dict:
        """Get info about all click-here fields (name, direction, memo)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                fields = controller.get_field_info()
                return {"success": True, "fields": fields, "count": len(fields)}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_field_exists(field_name: str) -> dict:
        """Check if a field with the given name exists."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                exists = controller.field_exists(field_name)
                return {"success": True, "exists": exists, "field": field_name}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_delete_field() -> dict:
        """Delete the click-here field at cursor (keeps content)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.delete_field()
                return {
                    "success": success,
                    "message": "Deleted field structure" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Advanced Table Operations ===

    @mcp.tool()
    def hwp_get_table_dimensions(as_unit: str = "mm") -> dict:
        """Get current table dimensions (width, height, row height, col width)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                return {
                    "success": True,
                    "width": controller.get_table_width(as_unit),
                    "height": controller.get_table_height(as_unit),
                    "row_height": controller.get_row_height(as_unit),
                    "col_width": controller.get_col_width(as_unit),
                    "unit": as_unit,
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_table_margins(as_unit: str = "mm") -> dict:
        """Get table outside margins and cell inside margins."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                return {
                    "success": True,
                    "outside": controller.get_table_outside_margin(as_unit),
                    "cell_inside": controller.get_cell_margin(as_unit),
                    "unit": as_unit,
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_into_table(table_index: int = 0) -> dict:
        """Move cursor into the Nth table (0-indexed)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.get_into_table(table_index)
                return {
                    "success": success,
                    "message": f"Moved into table {table_index}"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Advanced Selection & Navigation ===

    @mcp.tool()
    def hwp_select_text_range(
        slist: int, spara: int, spos: int, elist: int, epara: int, epos: int
    ) -> dict:
        """Select a text range by position coordinates (Start: list,para,pos / End: list,para,pos)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.select_text(slist, spara, spos, elist, epara, epos)
                return {
                    "success": success,
                    "message": "Selected range" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_navigation(action: str) -> dict:
        """Perform navigation action. action: 'next_para', 'prev_para', 'next_word', 'prev_word', 'cancel_selection', 'close_list'."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                actions = {
                    "next_para": controller.move_next_para,
                    "prev_para": controller.move_prev_para,
                    "next_word": controller.move_next_word,
                    "prev_word": controller.move_prev_word,
                    "cancel_selection": controller.cancel_selection,
                    "close_list": controller.close_list,
                }

                if action not in actions:
                    return {
                        "success": False,
                        "message": f"Invalid action. Valid: {list(actions.keys())}",
                    }

                success = actions[action]()
                return {
                    "success": success,
                    "message": f"Executed {action}" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_selection_action(action: str) -> dict:
        """Perform selection action. action: 'para', 'word', 'line'."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                actions = {
                    "para": controller.select_para,
                    "word": controller.select_word,
                    "line": controller.select_line,
                }

                if action not in actions:
                    return {
                        "success": False,
                        "message": f"Invalid action. Valid: {list(actions.keys())}",
                    }

                success = actions[action]()
                return {
                    "success": success,
                    "message": f"Selected {action}" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_delete_action(action: str) -> dict:
        """Perform delete action. action: 'word', 'line'."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                actions = {
                    "word": controller.delete_word,
                    "line": controller.delete_line,
                }

                if action not in actions:
                    return {
                        "success": False,
                        "message": f"Invalid action. Valid: {list(actions.keys())}",
                    }

                success = actions[action]()
                return {
                    "success": success,
                    "message": f"Deleted {action}" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_clear(option: int = 1) -> dict:
        """Clear document content. option: 0=ask, 1=discard(default), 2=save if dirty."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.clear_document(option)
                return {
                    "success": success,
                    "message": "Document cleared" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Header/Footer Operations ===

    @mcp.tool()
    def hwp_header_footer_modify() -> dict:
        """Enter header/footer edit mode to modify headers and footers."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.header_footer_modify()
                return {
                    "success": success,
                    "message": "Entered header/footer edit mode"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_header_footer_delete() -> dict:
        """Delete the current header/footer."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.header_footer_delete()
                return {
                    "success": success,
                    "message": "Header/footer deleted" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Quick Bookmarks ===

    @mcp.tool()
    def hwp_quick_mark_insert(index: int) -> dict:
        """Insert quick bookmark (0-9) at current cursor position."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.quick_mark_insert(index)
                return {
                    "success": success,
                    "message": f"Quick mark {index} inserted" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_quick_mark_move(index: int) -> dict:
        """Move cursor to quick bookmark (0-9)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.quick_mark_move(index)
                return {
                    "success": success,
                    "message": f"Moved to quick mark {index}" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === File/Document Info ===

    @mcp.tool()
    def hwp_get_file_info(filepath: str) -> dict:
        """Get file info without opening (encryption, version, format)."""
        try:
            controller = _get_controller()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                info = controller.get_file_info(filepath)
                return {"success": True, **info}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_font_list() -> dict:
        """Get list of fonts used in current document."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                fonts = controller.get_font_list()
                return {"success": True, "fonts": fonts, "count": len(fonts)}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Control Manipulation ===

    @mcp.tool()
    def hwp_get_ctrl_by_id(ctrl_id: str) -> dict:
        """Get all controls by type ID (tbl, gso, pic, eqed, etc.)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                ctrls = controller.get_ctrl_by_ctrl_id(ctrl_id)
                return {"success": True, "controls": ctrls, "count": len(ctrls)}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_image_info() -> dict:
        """Get image information for current selected image (name, dimensions)."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                info = controller.get_image_info()
                return {"success": True, **info}
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Page Operations ===

    @mcp.tool()
    def hwp_copy_page() -> dict:
        """Copy entire current page."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.copy_page()
                return {
                    "success": success,
                    "message": "Page copied" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_paste_page() -> dict:
        """Paste copied page."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.paste_page()
                return {
                    "success": success,
                    "message": "Page pasted" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_delete_page() -> dict:
        """Delete current page."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.delete_page()
                return {
                    "success": success,
                    "message": "Page deleted" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Tab/Window Management ===

    @mcp.tool()
    def hwp_add_tab() -> dict:
        """Add new document tab in current window."""
        try:
            controller = _get_controller()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.add_tab()
                return {
                    "success": success,
                    "message": "New tab added" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_switch_to_document(doc_index: int) -> dict:
        """Switch to document by index (0-based)."""
        try:
            controller = _get_controller()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.switch_to_document(doc_index)
                return {
                    "success": success,
                    "message": f"Switched to document {doc_index}"
                    if success
                    else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Spell Check ===

    @mcp.tool()
    def hwp_auto_spell_run() -> dict:
        """Toggle automatic spell check on/off."""
        try:
            controller = _ensure_document()
            if controller.platform != Platform.WINDOWS:
                return {"success": False, "message": "Only available on Windows"}

            from .windows_hwp_controller_v2 import WindowsHwpControllerV2

            if isinstance(controller, WindowsHwpControllerV2):
                success = controller.auto_spell_run()
                return {
                    "success": success,
                    "message": "Spell check toggled" if success else "Failed",
                }
            return {"success": False, "message": "Invalid controller type"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Format Conversion ===

    @mcp.tool()
    def hwp_convert_hwp_to_hwpx(
        input_path: str, output_path: Optional[str] = None
    ) -> dict:
        """Convert HWP binary file to HWPX (Open XML) format.

        Opens an HWP file and saves it as HWPX format using the HWP application's
        built-in conversion capability. This is useful for converting legacy HWP
        files to the modern HWPX format.

        Args:
            input_path: Absolute path to the input .hwp file
            output_path: Path for output .hwpx file (optional).
                         Default: same directory and name with .hwpx extension

        Returns:
            dict with keys:
                - success: bool
                - output_path: str (path to converted file, if successful)
                - message: str (error message if failed)

        Platform Support:
            - Windows: Full support via HWP application
            - macOS/Linux: Not supported (HWP application required)
        """
        try:
            if not os.path.exists(input_path):
                return {
                    "success": False,
                    "message": f"Input file not found: {input_path}",
                }

            if not input_path.lower().endswith(".hwp"):
                return {
                    "success": False,
                    "message": "Input file must be .hwp format",
                }

            if output_path is None:
                output_path = os.path.splitext(input_path)[0] + ".hwpx"

            controller = _get_controller()

            if controller.platform != Platform.WINDOWS:
                return {
                    "success": False,
                    "message": "HWP to HWPX conversion requires Windows with HWP application installed",
                }

            if not controller.open_document(input_path):
                return {
                    "success": False,
                    "message": f"Failed to open input file: {input_path}",
                }

            success = controller.save_as(output_path, format="hwpx")
            controller.close_document(save=False)

            if success:
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": f"Successfully converted to: {output_path}",
                }
            else:
                return {
                    "success": False,
                    "message": "Conversion failed during save_as operation",
                }

        except Exception as e:
            return {"success": False, "message": str(e)}

    # === Template Management Tools ===

    @mcp.tool()
    def hwp_list_templates() -> dict:
        """List all available HWPX templates with their descriptions.

        Returns a list of templates that can be used with hwp_use_template.
        Each template has metadata including name, description, and category.

        Returns:
            dict with keys:
                - success: bool
                - templates: list of template metadata
                - count: number of available templates
        """
        try:
            import json

            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
            )
            index_path = os.path.join(templates_dir, "template_index.json")

            if not os.path.exists(index_path):
                return {
                    "success": False,
                    "message": f"Template index not found: {index_path}",
                }

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            templates = []
            for t in data.get("templates", []):
                templates.append(
                    {
                        "id": t["id"],
                        "name_ko": t["name_ko"],
                        "name_en": t["name_en"],
                        "category": t["category"],
                        "description_ko": t["description_ko"],
                        "description_en": t["description_en"],
                    }
                )

            return {
                "success": True,
                "templates": templates,
                "count": len(templates),
                "categories": data.get("categories", {}),
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_recommend_template(request: str, language: str = "auto") -> dict:
        """Recommend templates based on user requirements.

        Analyzes the user's request and returns matching templates sorted by relevance.
        Uses keyword matching against template descriptions and keywords.

        Args:
            request: User's description of what they need (e.g., "이력서", "resume", "보고서 작성")
            language: Response language - "ko", "en", or "auto" (detect from request)

        Returns:
            dict with keys:
                - success: bool
                - recommendations: list of matching templates with scores
                - best_match: the most suitable template
        """
        try:
            import json
            import re

            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
            )
            index_path = os.path.join(templates_dir, "template_index.json")

            if not os.path.exists(index_path):
                return {
                    "success": False,
                    "message": f"Template index not found: {index_path}",
                }

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if language == "auto":
                has_korean = bool(re.search(r"[가-힣]", request))
                language = "ko" if has_korean else "en"

            request_lower = request.lower()
            request_words = set(re.findall(r"\w+", request_lower))

            scored_templates = []
            for t in data.get("templates", []):
                score = 0

                for keyword in t.get("keywords", []):
                    if keyword.lower() in request_lower:
                        score += 10
                    if keyword.lower() in request_words:
                        score += 5

                if (
                    t["name_ko"].lower() in request_lower
                    or t["name_en"].lower() in request_lower
                ):
                    score += 20

                desc = t["description_ko"] + " " + t["description_en"]
                for word in request_words:
                    if len(word) > 1 and word in desc.lower():
                        score += 3

                if t["category"].lower() in request_lower:
                    score += 15

                if score > 0:
                    scored_templates.append(
                        {
                            "id": t["id"],
                            "filename": t["filename"],
                            "name": t["name_ko"] if language == "ko" else t["name_en"],
                            "description": t["description_ko"]
                            if language == "ko"
                            else t["description_en"],
                            "category": t["category"],
                            "score": score,
                        }
                    )

            scored_templates.sort(key=lambda x: x["score"], reverse=True)
            recommendations = scored_templates[:5]

            if not recommendations:
                return {
                    "success": True,
                    "recommendations": [],
                    "best_match": None,
                    "message": "No matching templates found. Try different keywords or use hwp_list_templates to see all available templates.",
                }

            return {
                "success": True,
                "recommendations": recommendations,
                "best_match": recommendations[0] if recommendations else None,
                "language": language,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_use_template(template_id: str, output_path: str) -> dict:
        """Clone a template and open the copy for editing.

        Creates a copy of the specified template at the output path and opens it
        for editing. The original template remains unchanged.

        Args:
            template_id: Template ID (e.g., "h02_design_resume") or filename (e.g., "h02_design_resume.hwpx")
            output_path: Path where the cloned template will be saved.
                        Must be an absolute path ending with .hwpx

        Returns:
            dict with keys:
                - success: bool
                - output_path: path to the cloned file
                - template_id: the template that was used
                - message: status message

        Example:
            hwp_use_template("h02_design_resume", "/Users/name/Documents/my_resume.hwpx")
        """
        try:
            import shutil
            import json

            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
            )
            index_path = os.path.join(templates_dir, "template_index.json")

            template_filename = None
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for t in data.get("templates", []):
                    if t["id"] == template_id or t["filename"] == template_id:
                        template_filename = t["filename"]
                        break

            if not template_filename:
                if template_id.endswith(".hwpx"):
                    template_filename = template_id
                else:
                    template_filename = template_id + ".hwpx"

            template_path = os.path.join(templates_dir, template_filename)

            if not os.path.exists(template_path):
                return {
                    "success": False,
                    "message": f"Template not found: {template_filename}. Use hwp_list_templates to see available templates.",
                }

            if not output_path.lower().endswith(".hwpx"):
                output_path = output_path + ".hwpx"

            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            shutil.copy2(template_path, output_path)

            controller = _get_controller()
            success = controller.open_document(output_path)

            if success:
                return {
                    "success": True,
                    "output_path": output_path,
                    "template_id": template_id,
                    "message": f"Template cloned and opened: {output_path}",
                }
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "template_id": template_id,
                    "message": f"Template cloned to {output_path} but failed to open. You can open it manually.",
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def hwp_get_template_info(template_id: str) -> dict:
        """Get detailed information about a specific template.

        Args:
            template_id: Template ID (e.g., "h02_design_resume")

        Returns:
            dict with full template metadata including keywords and descriptions
        """
        try:
            import json

            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
            )
            index_path = os.path.join(templates_dir, "template_index.json")

            if not os.path.exists(index_path):
                return {
                    "success": False,
                    "message": f"Template index not found: {index_path}",
                }

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for t in data.get("templates", []):
                if (
                    t["id"] == template_id
                    or t["filename"] == template_id
                    or t["filename"] == template_id + ".hwpx"
                ):
                    template_path = os.path.join(templates_dir, t["filename"])
                    return {
                        "success": True,
                        "template": {
                            **t,
                            "path": template_path,
                            "exists": os.path.exists(template_path),
                        },
                    }

            return {
                "success": False,
                "message": f"Template not found: {template_id}. Use hwp_list_templates to see available templates.",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Unified HWP tools registered")
