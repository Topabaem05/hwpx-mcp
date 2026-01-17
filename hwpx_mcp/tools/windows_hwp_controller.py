"""
Windows HWP Controller using pywin32 COM automation

This module provides HWP document control using Windows COM automation.
Only available on Windows platform with HWP installed.
"""

import sys
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("hwp-mcp-extended.windows_controller")

# Check if running on Windows
IS_WINDOWS = sys.platform == "win32"


@dataclass
class HwpDocumentInfo:
    """HWP document information"""

    path: str
    text_length: int
    paragraphs_count: int
    tables_count: int
    images_count: int
    pages_count: int
    file_size: int
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None


class WindowsHwpController:
    """HWP Controller using pywin32 COM automation (Windows only)"""

    def __init__(self):
        """Initialize HWP controller."""
        self.hwp = None
        self._is_hwp_running = False
        self._is_document_open = False
        self.visible = True
        self.current_document_path = None

        if not IS_WINDOWS:
            logger.warning("WindowsHwpController only works on Windows")
            return

        try:
            import win32com.client

            self.hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
            self._is_hwp_running = True
            logger.info("HWP COM connection established")
        except Exception as e:
            logger.error(f"Failed to connect to HWP: {e}")
            self.hwp = None
            self._is_hwp_running = False

    def connect(
        self, visible: bool = True, register_security_module: bool = True
    ) -> bool:
        """
        Connect to HWP application with optional security module registration.

        Args:
            visible (bool): Show HWP window
            register_security_module (bool): Register security module to prevent popups

        Returns:
            bool: Success status
        """
        if not IS_WINDOWS:
            logger.error("Not running on Windows")
            return False

        if not self.hwp:
            try:
                import win32com.client

                self.hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
            except Exception as e:
                logger.error(f"Failed to connect to HWP: {e}")
                return False

        try:
            # Register security module if requested
            if register_security_module:
                try:
                    # Try to find security module in project directory
                    module_path = os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "..",
                        "security_module",
                        "FilePathCheckerModuleExample.dll",
                    )
                    if not os.path.exists(module_path):
                        # Fall back to common installation paths
                        module_path = "D:/hwp-mcp/security_module/FilePathCheckerModuleExample.dll"

                    if os.path.exists(module_path):
                        self.hwp.RegisterModule(
                            "FilePathCheckerModuleExample", module_path
                        )
                        logger.info("Security module registered successfully")
                    else:
                        logger.warning(f"Security module not found at: {module_path}")
                except Exception as e:
                    logger.warning(
                        f"Security module registration failed (continuing): {e}"
                    )

            self.visible = visible
            if hasattr(self.hwp, "XHwpWindows"):
                self.hwp.XHwpWindows.Item(0).Visible = visible
            self._is_hwp_running = True
            return True

        except Exception as e:
            logger.error(f"Failed to configure HWP: {e}")
            return False

    @property
    def is_hwp_running(self) -> bool:
        """Check if HWP is running."""
        return self._is_hwp_running and self.hwp is not None

    @property
    def is_document_open(self) -> bool:
        """Check if a document is open."""
        return self._is_document_open and self.is_hwp_running

    def open_document(self, file_path: str) -> bool:
        """Open HWP document.

        Args:
            file_path: Path to HWP file

        Returns:
            bool: Success status
        """
        if not self.is_hwp_running:
            logger.error("HWP not running")
            return False

        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            self.hwp.Open(file_path)
            self._is_document_open = True
            logger.info(f"Opened: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            return False

    def create_new_document(self) -> bool:
        """Create new document.

        Returns:
            bool: Success status
        """
        if not self.is_hwp_running:
            return False

        try:
            self.hwp.Create()
            self._is_document_open = True
            logger.info("Created new document")
            return True
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return False

    def close_document(self) -> bool:
        """Close current document.

        Returns:
            bool: Success status
        """
        if not self.is_hwp_running:
            return False

        try:
            if self._is_document_open:
                self.hwp.Clear(1)  # 1 = without save
                self._is_document_open = False
            return True
        except Exception as e:
            logger.error(f"Failed to close document: {e}")
            return False

    def quit(self) -> None:
        """Quit HWP application."""
        if self.is_hwp_running:
            try:
                self.hwp.Quit()
                self.hwp = None
                self._is_hwp_running = False
                self._is_document_open = False
                logger.info("HWP quit")
            except Exception as e:
                logger.error(f"Failed to quit HWP: {e}")

    def save_document(self, file_path: str) -> bool:
        """Save document.

        Args:
            file_path: Save path

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.SaveAs(file_path)
            logger.info(f"Saved: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return False

    def get_text(self) -> str:
        """Get all text from document.

        Returns:
            str: Document text
        """
        if not self.is_document_open:
            return ""

        try:
            return self.hwp.GetText()
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return ""

    def insert_text(self, text: str, preserve_linebreaks: bool = True) -> bool:
        """Insert text at cursor position.

        Args:
            text: Text to insert
            preserve_linebreaks: If True, preserve newline characters as paragraph breaks

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            # Check if cursor is inside a table
            is_in_table = False
            try:
                self.hwp.Run("TableCellBlock")
                self.hwp.Run("Cancel")
                is_in_table = True
            except Exception:
                is_in_table = False

            # Handle escaped newlines and actual newlines
            if preserve_linebreaks and ("\n" in text or "\\n" in text):
                # Convert escaped newlines to actual newlines
                processed_text = text.replace("\\n", "\n")
                lines = processed_text.split("\n")

                for i, line in enumerate(lines):
                    if not self._insert_text_direct(line):
                        return False
                    # Insert paragraph break after each line except the last
                    if i < len(lines) - 1:
                        self.insert_paragraph()

                return True
            else:
                success = self._insert_text_direct(text)
                # Move cursor right after text if not in table
                if success and not is_in_table:
                    try:
                        for _ in range(len(text)):
                            self.hwp.Run("CharRight")
                    except Exception:
                        pass
                return success

        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False

    def save_as_format(self, file_path: str, format_type: str) -> bool:
        """Save document in specific format (HWP, HWPX, PDF, HTML)."""
        if not self.is_document_open:
            return False

        try:
            return self.hwp.SaveAs(file_path, format_type, "")
        except Exception as e:
            logger.error(f"Failed to save as {format_type}: {e}")
            return False

    def _insert_text_direct(self, text: str) -> bool:
        """Insert text directly using HAction API.

        Args:
            text: Text to insert

        Returns:
            bool: Success status
        """
        try:
            self.hwp.HAction.GetDefault(
                "InsertText", self.hwp.HParameterSet.HInsertText.HSet
            )
            self.hwp.HParameterSet.HInsertText.Text = text
            self.hwp.HAction.Execute(
                "InsertText", self.hwp.HParameterSet.HInsertText.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert text directly: {e}")
            return False

    def insert_paragraph(self) -> bool:
        """Insert paragraph break."""
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.Run("BreakPara")
            return True
        except Exception as e:
            logger.error(f"Failed to insert paragraph: {e}")
            return False

    def set_font_style(
        self,
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        select_previous_text: bool = False,
    ) -> bool:
        """
        Set font style with Korean/English font support.

        Args:
            font_name: Font name (applies to all language types)
            font_size: Font size in points (hwpunit = font_size * 100)
            bold: Bold text
            italic: Italic text
            underline: Underline text
            select_previous_text: Select previously entered text

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            if select_previous_text:
                self.select_last_text()

            self.hwp.HAction.GetDefault(
                "CharShape", self.hwp.HParameterSet.HCharShape.HSet
            )

            if font_name:
                self.hwp.HParameterSet.HCharShape.FaceNameHangul = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameLatin = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameHanja = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameJapanese = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameOther = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameSymbol = font_name
                self.hwp.HParameterSet.HCharShape.FaceNameUser = font_name

            if font_size:
                self.hwp.HParameterSet.HCharShape.Height = font_size * 100

            self.hwp.HParameterSet.HCharShape.Bold = bold
            self.hwp.HParameterSet.HCharShape.Italic = italic
            self.hwp.HParameterSet.HCharShape.UnderlineType = 1 if underline else 0

            self.hwp.HAction.Execute(
                "CharShape", self.hwp.HParameterSet.HCharShape.HSet
            )
            return True

        except Exception as e:
            logger.error(f"Failed to set font style: {e}")
            return False

    def select_last_text(self) -> bool:
        """Select the last entered text in current paragraph."""
        if not self.is_document_open:
            return False

        try:
            current_pos = self.hwp.GetPos()
            if not current_pos:
                return False

            self.hwp.Run("MoveLineStart")
            start_pos = self.hwp.GetPos()

            self.hwp.SetPos(*start_pos)
            self.hwp.SelectText(start_pos, current_pos)

            return True
        except Exception as e:
            logger.error(f"Failed to select last text: {e}")
            return False

    def set_font(
        self,
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
        bold: bool = False,
    ) -> bool:
        """Set font properties (legacy method).

        Args:
            font_name: Font name
            font_size: Font size
            bold: Bold

        Returns:
            bool: Success status
        """
        return self.set_font_style(
            font_name=font_name,
            font_size=font_size,
            bold=bold,
            select_previous_text=False,
        )

    def search_text(self, query: str) -> List[int]:
        """Search text in document.

        Args:
            query: Search query

        Returns:
            List[int]: List of line numbers where found
        """
        if not self.is_document_open:
            return []

        try:
            results = []
            self.hwp.FindInit()
            while True:
                pos = self.hwp.FindNext()
                if pos <= 0:
                    break
                # Get current position info
                results.append(pos)
            return results
        except Exception as e:
            logger.error(f"Failed to search text: {e}")
            return []

    def replace_text(self, find_text: str, replace_text: str) -> int:
        """Replace text.

        Args:
            find_text: Text to find
            replace_text: Text to replace

        Returns:
            int: Number of replacements
        """
        if not self.is_document_open:
            return 0

        try:
            count = 0
            self.hwp.FindInit()
            while self.hwp.FindReplace(find_text, replace_text, 1):  # 1 = replace all
                count += 1
            return count
        except Exception as e:
            logger.error(f"Failed to replace text: {e}")
            return 0

    def fill_table_with_data(
        self,
        data: List[List[str]],
        start_row: int = 1,
        start_col: int = 1,
        has_header: bool = False,
    ) -> bool:
        """
        Fill table with 2D data array.

        Args:
            data (List[List[str]]): 2D data array (rows x cols)
            start_row (int): Starting row number (1-based)
            start_col (int): Starting column number (1-based)
            has_header (bool): Treat first row as header

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.Run("TableSelCell")
            self.hwp.Run("TableSelTable")
            self.hwp.Run("Cancel")
            self.hwp.Run("TableSelCell")
            self.hwp.Run("Cancel")

            for _ in range(start_row - 1):
                self.hwp.Run("TableLowerCell")
            for _ in range(start_col - 1):
                self.hwp.Run("TableRightCell")

            for row_idx, row_data in enumerate(data):
                for col_idx, cell_value in enumerate(row_data):
                    self.hwp.Run("TableSelCell")
                    self.hwp.Run("Delete")
                    if has_header and row_idx == 0:
                        self.set_font_style(bold=True)
                        self.hwp.HAction.GetDefault(
                            "InsertText", self.hwp.HParameterSet.HInsertText.HSet
                        )
                        self.hwp.HParameterSet.HInsertText.Text = str(cell_value)
                        self.hwp.HAction.Execute(
                            "InsertText", self.hwp.HParameterSet.HInsertText.HSet
                        )
                        self.set_font_style(bold=False)
                    else:
                        self.hwp.HAction.GetDefault(
                            "InsertText", self.hwp.HParameterSet.HInsertText.HSet
                        )
                        self.hwp.HParameterSet.HInsertText.Text = str(cell_value)
                        self.hwp.HAction.Execute(
                            "InsertText", self.hwp.HParameterSet.HInsertText.HSet
                        )

                    if col_idx < len(row_data) - 1:
                        self.hwp.Run("TableRightCell")

                if row_idx < len(data) - 1:
                    for _ in range(len(row_data) - 1):
                        self.hwp.Run("TableLeftCell")
                    self.hwp.Run("TableLowerCell")

            self.hwp.Run("TableSelCell")
            self.hwp.Run("Cancel")
            self.hwp.Run("MoveDown")

            return True

        except Exception as e:
            logger.error(f"Failed to fill table with data: {e}")
            return False

    def create_document_from_text(self, text: str, auto_format: bool = True) -> bool:
        """
        Create document from text with optional auto-formatting.

        Args:
            text: Text content to insert
            auto_format: Apply automatic formatting

        Returns:
            bool: Success status
        """
        if not self.is_hwp_running:
            if not self.connect():
                return False

        try:
            if not self.create_new_document():
                return False

            if auto_format:
                # Insert text with paragraph breaks
                paragraphs = text.split("\n")
                for i, paragraph in enumerate(paragraphs):
                    if paragraph.strip():
                        self.insert_text(paragraph)
                    if i < len(paragraphs) - 1:
                        self.insert_paragraph()
            else:
                self.insert_text(text)

            return True
        except Exception as e:
            logger.error(f"Failed to create document from text: {e}")
            return False

    def batch_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute multiple operations in batch.

        Args:
            operations: List of operation dictionaries

        Returns:
            Dict: Results of batch execution
        """
        results = []

        if not self.is_document_open:
            return {"success": False, "results": [], "error": "No document open"}

        try:
            for operation in operations:
                op_type = operation.get("type")
                op_data = operation.get("data", {})

                try:
                    if op_type == "insert_text":
                        result = self.insert_text(op_data.get("text", ""))
                    elif op_type == "set_font_style":
                        result = self.set_font_style(**op_data)
                    elif op_type == "insert_paragraph":
                        result = self.insert_paragraph()
                    elif op_type == "insert_table":
                        result = self.insert_table(
                            op_data.get("rows", 1), op_data.get("cols", 1)
                        )
                    else:
                        result = {
                            "success": False,
                            "error": f"Unknown operation: {op_type}",
                        }

                    results.append(
                        {
                            "type": op_type,
                            "success": result
                            if isinstance(result, bool)
                            else result.get("success", False),
                            "data": op_data,
                        }
                    )

                except Exception as op_error:
                    results.append(
                        {
                            "type": op_type,
                            "success": False,
                            "error": str(op_error),
                            "data": op_data,
                        }
                    )

            return {
                "success": True,
                "results": results,
                "total_operations": len(operations),
            }

        except Exception as e:
            logger.error(f"Batch operations failed: {e}")
            return {
                "success": False,
                "results": results,
                "error": str(e),
                "total_operations": len(operations),
            }

    def insert_image(
        self, image_path: str, width: int = 0, height: int = 0, embedded: bool = True
    ) -> bool:
        """Insert image at cursor position.

        Args:
            image_path: Path to image file
            width: Image width (mm), 0 for original size
            height: Image height (mm), 0 for original size
            embedded: Embed image in document

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            abs_path = os.path.abspath(image_path)
            if not os.path.exists(abs_path):
                logger.error(f"Image file not found: {abs_path}")
                return False

            self.hwp.HAction.GetDefault(
                "InsertPicture", self.hwp.HParameterSet.HInsertPicture.HSet
            )
            self.hwp.HParameterSet.HInsertPicture.FileName = abs_path
            self.hwp.HParameterSet.HInsertPicture.Width = width
            self.hwp.HParameterSet.HInsertPicture.Height = height
            self.hwp.HParameterSet.HInsertPicture.Embed = 1 if embedded else 0

            result = self.hwp.HAction.Execute(
                "InsertPicture", self.hwp.HParameterSet.HInsertPicture.HSet
            )

            if not result:
                logger.error("Failed to execute InsertPicture action")
                return False

            return True
        except Exception as e:
            logger.error(f"Failed to insert image: {e}")
            return False

    def put_field_text(self, field_list: str, text_list: str) -> bool:
        """Put text into fields.

        Args:
            field_list: Field names separated by \x02
            text_list: Text values separated by \x02

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.PutFieldText(field_list, text_list)
            return True
        except Exception as e:
            logger.error(f"Failed to put field text: {e}")
            return False

    def get_field_text(self, field_list: str) -> str:
        """Get text from fields.

        Args:
            field_list: Field names separated by \x02

        Returns:
            str: Field text values separated by \x02
        """
        if not self.is_document_open:
            return ""

        try:
            return self.hwp.GetFieldText(field_list)
        except Exception as e:
            logger.error(f"Failed to get field text: {e}")
            return ""

    def create_page_image(
        self,
        output_path: str,
        page_no: int = 0,
        resolution: int = 96,
        depth: int = 24,
        fmt: str = "png",
    ) -> bool:
        """Create image from page.

        Args:
            output_path: Output image path
            page_no: Page number (0-based)
            resolution: DPI (default 96)
            depth: Color depth (default 24)
            fmt: Image format (bmp, gif, jpeg, png)

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            abs_path = os.path.abspath(output_path)
            return self.hwp.CreatePageImage(abs_path, page_no, resolution, depth, fmt)
        except Exception as e:
            logger.error(f"Failed to create page image: {e}")
            return False

    def insert_memo(
        self, content: str, author: str = "Assistant", date_time: str = ""
    ) -> bool:
        """Insert memo at cursor position.

        Args:
            content: Memo content
            author: Memo author
            date_time: Memo date/time string

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.InsertMemo(content, author, date_time)
            return True
        except Exception as e:
            logger.error(f"Failed to insert memo: {e}")
            return False

    def insert_table(self, rows: int, cols: int) -> bool:
        """Insert table at cursor position."""
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "TableCreate", self.hwp.HParameterSet.HTableCreation.HSet
            )
            self.hwp.HParameterSet.HTableCreation.Rows = rows
            self.hwp.HParameterSet.HTableCreation.Cols = cols
            self.hwp.HParameterSet.HTableCreation.WidthType = 0
            self.hwp.HParameterSet.HTableCreation.HeightType = 1
            self.hwp.HParameterSet.HTableCreation.WidthValue = 0
            self.hwp.HParameterSet.HTableCreation.HeightValue = 1000

            col_width = 8000 // cols
            self.hwp.HParameterSet.HTableCreation.CreateItemArray("ColWidth", cols)
            for i in range(cols):
                self.hwp.HParameterSet.HTableCreation.ColWidth.SetItem(i, col_width)

            self.hwp.HAction.Execute(
                "TableCreate", self.hwp.HParameterSet.HTableCreation.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert table: {e}")
            return False

    def get_info(self) -> Optional[HwpDocumentInfo]:
        """Get document information.

        Returns:
            HwpDocumentInfo: Document info
        """
        if not self.is_document_open:
            return None

        try:
            text = self.get_text()
            paragraphs = [p for p in text.split("\n") if p.strip()]

            file_path = ""
            try:
                file_path = self.hwp.Path
            except Exception:
                pass

            file_size = 0
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)

            return HwpDocumentInfo(
                path=file_path,
                text_length=len(text),
                paragraphs_count=len(paragraphs),
                tables_count=text.count("표"),
                images_count=0,
                pages_count=max(1, len(paragraphs) // 30),
                file_size=file_size,
            )
        except Exception as e:
            logger.error(f"Failed to get info: {e}")
            return None

    def get_paragraphs(self, max_count: int = 100) -> List[Dict[str, Any]]:
        """Get paragraphs.

        Args:
            max_count: Maximum number of paragraphs

        Returns:
            List[Dict]: Paragraph list
        """
        if not self.is_document_open:
            return []

        try:
            text = self.get_text()
            paragraphs = [p for p in text.split("\n") if p.strip()][:max_count]

            return [
                {
                    "index": i,
                    "text": para,
                    "length": len(para),
                    "words_count": len(para.split()),
                }
                for i, para in enumerate(paragraphs)
            ]
        except Exception as e:
            logger.error(f"Failed to get paragraphs: {e}")
            return []

    def create_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: str = "",
    ) -> bool:
        """Create chart (placeholder - requires additional implementation).

        Args:
            chart_type: Chart type
            data: Chart data
            title: Chart title

        Returns:
            bool: Success status
        """
        # Chart insertion in HWP requires OLE automation
        # This is a placeholder for future implementation
        logger.warning("Chart creation via HWP COM not yet implemented")
        return False

    def create_equation(self, equation: str) -> bool:
        """Create equation (placeholder - requires additional implementation)."""
        logger.warning("Equation creation via HWP COM not yet implemented")
        return False

    def create_complete_document(self, document_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a complete document from specification."""
        try:
            if not self.is_hwp_running:
                if not self.connect():
                    return {"status": "error", "message": "Failed to connect to HWP"}

            if not self.create_new_document():
                return {"status": "error", "message": "Failed to create document"}

            if not document_spec:
                return {"status": "error", "message": "Document specification required"}

            elements = document_spec.get("elements", [])

            for element in elements:
                element_type = element.get("type", "")
                content = element.get("content", "")
                properties = element.get("properties", {})

                if element_type == "heading":
                    font_size = properties.get("font_size", 16)
                    bold = properties.get("bold", True)
                    self.set_font_style(font_size=font_size, bold=bold)
                    self._insert_text_direct(content)
                    self.insert_paragraph()

                elif element_type == "text":
                    font_size = properties.get("font_size", 10)
                    bold = properties.get("bold", False)
                    italic = properties.get("italic", False)
                    self.set_font_style(font_size=font_size, bold=bold, italic=italic)
                    self._insert_text_direct(content)

                elif element_type == "paragraph":
                    self.insert_paragraph()

                elif element_type == "table":
                    rows = properties.get("rows", 0)
                    cols = properties.get("cols", 0)
                    data = properties.get("data", [])
                    if rows > 0 and cols > 0:
                        self.insert_table(rows, cols)
                        if data:
                            str_data = [[str(cell) for cell in row] for row in data]
                            self.fill_table_with_data(str_data, 1, 1, False)

            save_path = None
            if document_spec.get("save", False):
                filename = document_spec.get("filename", "generated_document.hwp")
                if self.save_document(filename):
                    save_path = filename

            result = {"status": "success", "message": "Document created successfully"}
            if save_path:
                result["saved_path"] = save_path
            return result

        except Exception as e:
            logger.error(f"Error creating complete document: {e}")
            return {"status": "error", "message": str(e)}

    # ============================================================
    # HWP SDK Extended Features (from Actions.h, Document.h, etc.)
    # ============================================================

    def run_action(self, action_id: str) -> bool:
        """Execute any HWP action by ID (covers 800+ actions from Actions.h).

        Common action categories:
        - Edit: Copy, Cut, Paste, Delete, Undo, Redo, SelectAll
        - View: ViewZoom, ViewOption*
        - Formatting: CharShapeBold, CharShapeItalic, ParagraphShapeAlignCenter
        - Navigation: MovePageUp, MoveLineEnd, MoveDocBegin, MoveDocEnd
        - Table: TableDeleteRow, TableDeleteCol, TableDistributeCellWidth

        Args:
            action_id: HWP action ID string (e.g., "Copy", "MoveDocEnd")

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            result = self.hwp.HAction.Run(action_id)
            return result if isinstance(result, bool) else True
        except Exception as e:
            logger.error(f"Failed to run action '{action_id}': {e}")
            return False

    def page_setup(
        self,
        width_mm: Optional[float] = None,
        height_mm: Optional[float] = None,
        top_margin_mm: Optional[float] = None,
        bottom_margin_mm: Optional[float] = None,
        left_margin_mm: Optional[float] = None,
        right_margin_mm: Optional[float] = None,
        orientation: str = "portrait",
        paper_type: str = "custom",
    ) -> bool:
        """Set page layout (PageSetup action with ParameterSet).

        Args:
            width_mm: Page width in mm (default A4: 210mm)
            height_mm: Page height in mm (default A4: 297mm)
            top_margin_mm: Top margin in mm
            bottom_margin_mm: Bottom margin in mm
            left_margin_mm: Left margin in mm
            right_margin_mm: Right margin in mm
            orientation: 'portrait' or 'landscape'
            paper_type: 'a4', 'letter', 'legal', 'b5', 'custom'

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            # Paper type presets (width x height in mm)
            paper_sizes = {
                "a4": (210, 297),
                "letter": (216, 279),
                "legal": (216, 356),
                "b5": (182, 257),
                "a3": (297, 420),
            }

            if paper_type.lower() in paper_sizes:
                w, h = paper_sizes[paper_type.lower()]
                width_mm = width_mm or w
                height_mm = height_mm or h
            else:
                width_mm = width_mm or 210
                height_mm = height_mm or 297

            # Swap for landscape
            if orientation.lower() == "landscape":
                width_mm, height_mm = height_mm, width_mm

            # Convert mm to HwpUnit (1mm = 283.46 HwpUnit)
            MM_TO_HWPUNIT = 283.46

            self.hwp.HAction.GetDefault(
                "PageSetup", self.hwp.HParameterSet.HSecDef.HSet
            )

            self.hwp.HParameterSet.HSecDef.PageWidth = int(width_mm * MM_TO_HWPUNIT)
            self.hwp.HParameterSet.HSecDef.PageHeight = int(height_mm * MM_TO_HWPUNIT)

            if top_margin_mm is not None:
                self.hwp.HParameterSet.HSecDef.TopMargin = int(
                    top_margin_mm * MM_TO_HWPUNIT
                )
            if bottom_margin_mm is not None:
                self.hwp.HParameterSet.HSecDef.BottomMargin = int(
                    bottom_margin_mm * MM_TO_HWPUNIT
                )
            if left_margin_mm is not None:
                self.hwp.HParameterSet.HSecDef.LeftMargin = int(
                    left_margin_mm * MM_TO_HWPUNIT
                )
            if right_margin_mm is not None:
                self.hwp.HParameterSet.HSecDef.RightMargin = int(
                    right_margin_mm * MM_TO_HWPUNIT
                )

            self.hwp.HAction.Execute("PageSetup", self.hwp.HParameterSet.HSecDef.HSet)
            return True
        except Exception as e:
            logger.error(f"Failed to set page setup: {e}")
            return False

    def insert_page_number(
        self,
        position: int = 4,
        number_format: int = 0,
        starting_number: int = 1,
        side_char: str = "",
    ) -> bool:
        """Insert page numbering (PageNumPos action).

        Args:
            position: Position code (0=None, 1=TopLeft, 2=TopCenter, 3=TopRight,
                     4=BottomCenter, 5=BottomLeft, 6=BottomRight, 7=OutsideTop,
                     8=OutsideBottom, 9=InsideTop, 10=InsideBottom)
            number_format: Format (0=Arabic, 1=UpperRoman, 2=LowerRoman,
                          3=UpperAlpha, 4=LowerAlpha, 5=Circled, 6=Hangul)
            starting_number: Starting page number
            side_char: Side character (e.g., '-' for "- 1 -")

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "PageNumPos", self.hwp.HParameterSet.HPageNumPos.HSet
            )

            self.hwp.HParameterSet.HPageNumPos.DrawPos = position
            self.hwp.HParameterSet.HPageNumPos.NumFormat = number_format
            self.hwp.HParameterSet.HPageNumPos.NewNumber = starting_number

            if side_char:
                self.hwp.HParameterSet.HPageNumPos.SideChar = ord(side_char[0])

            self.hwp.HAction.Execute(
                "PageNumPos", self.hwp.HParameterSet.HPageNumPos.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert page number: {e}")
            return False

    def format_cell(
        self,
        fill_color: Optional[int] = None,
        border_type: int = 1,
        border_width: int = 1,
        apply_to_selection: bool = True,
    ) -> bool:
        """Format table cell with border and fill (CellBorderFill action).

        Args:
            fill_color: RGB color as integer (e.g., 0xFFFF00 for yellow)
            border_type: Border line type (0=None, 1=Solid, 2=Dash, etc.)
            border_width: Border line width (1=0.1mm, 5=0.5mm, 10=1mm)
            apply_to_selection: Apply to selected cells

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            if apply_to_selection:
                self.hwp.Run("TableCellBlock")

            self.hwp.HAction.GetDefault(
                "CellBorderFill", self.hwp.HParameterSet.HCellBorderFill.HSet
            )

            # Set border for all sides
            for side in ["Top", "Bottom", "Left", "Right"]:
                setattr(
                    self.hwp.HParameterSet.HCellBorderFill,
                    f"BorderType{side}",
                    border_type,
                )
                setattr(
                    self.hwp.HParameterSet.HCellBorderFill,
                    f"BorderWidth{side}",
                    border_width,
                )

            # Set fill color if provided
            if fill_color is not None:
                # Create nested FillAttr ItemSet
                fill_set = self.hwp.HParameterSet.HCellBorderFill.FillAttr
                fill_set.SetItem("WinBrushFaceColor", fill_color)
                fill_set.SetItem("WinBrushFaceStyle", -1)  # Solid fill

            self.hwp.HAction.Execute(
                "CellBorderFill", self.hwp.HParameterSet.HCellBorderFill.HSet
            )

            if apply_to_selection:
                self.hwp.Run("Cancel")

            return True
        except Exception as e:
            logger.error(f"Failed to format cell: {e}")
            return False

    def move_to_pos(
        self,
        move_id: str = "MoveDocEnd",
        para: int = 0,
        pos: int = 0,
    ) -> bool:
        """Move cursor to specific position (MovePos API).

        Args:
            move_id: Movement target ID (e.g., 'MoveDocBegin', 'MoveNextPara').
                     See README for full list of 37+ IDs.
            para: Paragraph index (for MoveMain, MoveCurList) or X coord (MoveScrPos)
            pos: Position index (for MoveMain, MoveCurList) or Y coord (MoveScrPos)

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            # Full MoveID map based on HWP SDK Document.h
            move_id_map = {
                "MoveMain": 0,
                "MoveCurList": 1,
                "MoveTopOfFile": 2,
                "MoveDocBegin": 2,  # Alias
                "MoveBottomOfFile": 3,
                "MoveDocEnd": 3,  # Alias
                "MoveTopOfList": 4,
                "MoveBottomOfList": 5,
                "MoveStartOfPara": 6,
                "MoveParaBegin": 6,  # Alias
                "MoveEndOfPara": 7,
                "MoveParaEnd": 7,  # Alias
                "MoveStartOfWord": 8,
                "MoveEndOfWord": 9,
                "MoveNextPara": 10,
                "MovePrevPara": 11,
                "MoveNextPos": 12,
                "MovePrevPos": 13,
                "MoveNextPosEx": 14,
                "MovePrevPosEx": 15,
                "MoveNextChar": 16,
                "MovePrevChar": 17,
                "MoveNextWord": 18,
                "MovePrevWord": 19,
                "MoveNextLine": 20,
                "MovePrevLine": 21,
                "MoveStartOfLine": 22,
                "MoveLineBegin": 22,  # Alias
                "MoveEndOfLine": 23,
                "MoveLineEnd": 23,  # Alias
                "MoveParentList": 24,
                "MoveTopLevelList": 25,
                "MoveRootList": 26,
                "MoveCurrentCaret": 27,
                "MoveLeftOfCell": 100,
                "MoveRightOfCell": 101,
                "MoveUpOfCell": 102,
                "MoveDownOfCell": 103,
                "MoveStartOfCell": 104,
                "MoveEndOfCell": 105,
                "MoveTopOfCell": 106,
                "MoveBottomOfCell": 107,
                "MoveScrPos": 200,
                "MoveScanPos": 201,
            }

            # Normalize input (case-insensitive check could be added if needed,
            # but strict mapping is safer for now)
            if move_id in move_id_map:
                numeric_id = move_id_map[move_id]
                # Pass para/pos only if relevant (0, 1, 200), otherwise 0
                if numeric_id in (0, 1, 200):
                    return self.hwp.MovePos(numeric_id, para, pos)
                else:
                    return self.hwp.MovePos(numeric_id, 0, 0)
            else:
                # Try as direct action string if not in map
                return self.run_action(move_id)
        except Exception as e:
            logger.error(f"Failed to move to position: {e}")
            return False

    def select_range(
        self,
        start_para: int,
        start_pos: int,
        end_para: int,
        end_pos: int,
    ) -> bool:
        """Select text range (SelectText API).

        Args:
            start_para: Starting paragraph index
            start_pos: Starting position within paragraph
            end_para: Ending paragraph index
            end_pos: Ending position within paragraph

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            result = self.hwp.SelectText(start_para, start_pos, end_para, end_pos)
            return result if isinstance(result, bool) else True
        except Exception as e:
            logger.error(f"Failed to select range: {e}")
            return False

    def insert_header_footer(
        self,
        header_or_footer: str = "header",
        content: str = "",
        apply_to: str = "all",
    ) -> bool:
        """Insert header or footer.

        Args:
            header_or_footer: 'header' or 'footer'
            content: Text content to insert
            apply_to: 'all', 'odd', 'even', 'first'

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            action = "InsertHeader" if header_or_footer == "header" else "InsertFooter"
            self.hwp.HAction.Run(action)

            if content:
                self._insert_text_direct(content)

            # Exit header/footer editing mode
            self.hwp.HAction.Run("CloseEx")
            return True
        except Exception as e:
            logger.error(f"Failed to insert {header_or_footer}: {e}")
            return False

    def insert_note(
        self,
        note_type: str = "footnote",
        content: str = "",
    ) -> bool:
        """Insert footnote or endnote.

        Args:
            note_type: 'footnote' or 'endnote'
            content: Note content

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            action = "InsertFootnote" if note_type == "footnote" else "InsertEndnote"
            self.hwp.HAction.Run(action)

            if content:
                self._insert_text_direct(content)

            # Return to main body
            self.hwp.HAction.Run("CloseEx")
            return True
        except Exception as e:
            logger.error(f"Failed to insert {note_type}: {e}")
            return False

    def set_edit_mode(self, mode: str = "edit") -> bool:
        """Set document edit mode.

        Args:
            mode: 'edit' (normal editing), 'readonly' (read-only), 'form' (form mode)

        Returns:
            bool: Success status
        """
        if not self.is_hwp_running:
            return False

        try:
            mode_map = {
                "edit": 0,
                "readonly": 1,
                "form": 2,
            }
            mode_value = mode_map.get(mode.lower(), 0)
            self.hwp.EditMode = mode_value
            return True
        except Exception as e:
            logger.error(f"Failed to set edit mode: {e}")
            return False

    def manage_metatags(
        self,
        action: str = "get",
        tag_name: str = "",
        tag_value: str = "",
    ) -> Any:
        """Manage document metatags (hidden metadata).

        Args:
            action: 'get', 'set', 'delete', 'list'
            tag_name: Tag name (for get/set/delete)
            tag_value: Tag value (for set)

        Returns:
            Any: Tag value for 'get', list for 'list', bool for others
        """
        if not self.is_document_open:
            return None if action in ("get", "list") else False

        try:
            if action == "get":
                return self.hwp.GetMetatag(tag_name)
            elif action == "set":
                self.hwp.SetMetatag(tag_name, tag_value)
                return True
            elif action == "delete":
                self.hwp.DeleteMetatag(tag_name)
                return True
            elif action == "list":
                # Get all metatags
                return self.hwp.GetMetatagList()
            else:
                logger.error(f"Unknown metatag action: {action}")
                return False
        except Exception as e:
            logger.error(f"Failed to manage metatags: {e}")
            return None if action in ("get", "list") else False

    def insert_background(
        self,
        image_path: str,
        embedded: bool = True,
        fill_option: str = "tile",
    ) -> bool:
        """Insert background image (InsertBackgroundPicture).

        Args:
            image_path: Path to background image
            embedded: Embed image in document
            fill_option: 'tile', 'center', 'stretch', 'fit'

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            abs_path = os.path.abspath(image_path)
            if not os.path.exists(abs_path):
                logger.error(f"Background image not found: {abs_path}")
                return False

            fill_map = {
                "tile": 0,
                "center": 1,
                "stretch": 2,
                "fit": 3,
            }
            fill_value = fill_map.get(fill_option.lower(), 0)

            self.hwp.HAction.GetDefault(
                "InsertBackgroundPicture",
                self.hwp.HParameterSet.HInsertBackgroundPicture.HSet,
            )

            self.hwp.HParameterSet.HInsertBackgroundPicture.FileName = abs_path
            self.hwp.HParameterSet.HInsertBackgroundPicture.Embed = 1 if embedded else 0
            self.hwp.HParameterSet.HInsertBackgroundPicture.FillArea = fill_value

            self.hwp.HAction.Execute(
                "InsertBackgroundPicture",
                self.hwp.HParameterSet.HInsertBackgroundPicture.HSet,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert background: {e}")
            return False

    def insert_bookmark(self, name: str) -> bool:
        """Insert bookmark at cursor position (Ctrl+K, B).

        Args:
            name: Bookmark name

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "Bookmark", self.hwp.HParameterSet.HBookmark.HSet
            )
            self.hwp.HParameterSet.HBookmark.Title = name
            self.hwp.HParameterSet.HBookmark.Command = 1  # Insert

            self.hwp.HAction.Execute("Bookmark", self.hwp.HParameterSet.HBookmark.HSet)
            return True
        except Exception as e:
            logger.error(f"Failed to insert bookmark: {e}")
            return False

    def insert_hyperlink(self, url: str, display_text: Optional[str] = None) -> bool:
        """Insert hyperlink at cursor position (Ctrl+K, H).

        Args:
            url: Target URL or path
            display_text: Text to display (if None, applies to selection or uses url)

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "InsertHyperlink", self.hwp.HParameterSet.HHyperlink.HSet
            )
            self.hwp.HParameterSet.HHyperlink.Command = url

            if display_text:
                self.hwp.HParameterSet.HHyperlink.Text = display_text

            self.hwp.HAction.Execute(
                "InsertHyperlink", self.hwp.HParameterSet.HHyperlink.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert hyperlink: {e}")
            return False

    def table_split_cell(self, rows: int = 2, cols: int = 1) -> bool:
        """Split current table cell.

        Args:
            rows: Number of rows to split into
            cols: Number of columns to split into

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "TableSplitCell", self.hwp.HParameterSet.HTableSplitCell.HSet
            )
            self.hwp.HParameterSet.HTableSplitCell.Rows = rows
            self.hwp.HParameterSet.HTableSplitCell.Cols = cols
            self.hwp.HParameterSet.HTableSplitCell.Merge = 0

            self.hwp.HAction.Execute(
                "TableSplitCell", self.hwp.HParameterSet.HTableSplitCell.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to split cell: {e}")
            return False

    def table_merge_cells(self) -> bool:
        """Merge selected table cells.

        Returns:
            bool: Success status
        """
        return self.run_action("TableMergeCell")

    def setup_columns(
        self, count: int = 1, same_size: bool = True, gap_mm: float = 10.0
    ) -> bool:
        """Configure page columns (MultiColumn).

        Args:
            count: Number of columns (1-4)
            same_size: Use same width for all columns
            gap_mm: Gap between columns in mm

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            # 1mm = 283.465 HwpUnit
            MM_TO_HWPUNIT = 283.465

            self.hwp.HAction.GetDefault(
                "MultiColumn", self.hwp.HParameterSet.HColDef.HSet
            )
            self.hwp.HParameterSet.HColDef.Count = count
            self.hwp.HParameterSet.HColDef.SameSize = 1 if same_size else 0
            self.hwp.HParameterSet.HColDef.Gap = int(gap_mm * MM_TO_HWPUNIT)

            self.hwp.HAction.Execute("MultiColumn", self.hwp.HParameterSet.HColDef.HSet)
            return True
        except Exception as e:
            logger.error(f"Failed to setup columns: {e}")
            return False

    def insert_dutmal(
        self, main_text: str, sub_text: str, position: str = "top"
    ) -> bool:
        """Insert Dutmal (text with comment above/below).

        Args:
            main_text: Main text body
            sub_text: Comment text (Dutmal)
            position: 'top' (above) or 'bottom' (below)

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "DutmalChars", self.hwp.HParameterSet.HDutmal.HSet
            )
            self.hwp.HParameterSet.HDutmal.Text = main_text
            self.hwp.HParameterSet.HDutmal.DutmalText = sub_text
            self.hwp.HParameterSet.HDutmal.Position = 1 if position == "bottom" else 0

            self.hwp.HAction.Execute("DutmalChars", self.hwp.HParameterSet.HDutmal.HSet)
            return True
        except Exception as e:
            logger.error(f"Failed to insert dutmal: {e}")
            return False

    def insert_index_mark(self, keyword1: str, keyword2: str = "") -> bool:
        """Insert Index Mark.

        Args:
            keyword1: Primary keyword
            keyword2: Secondary keyword

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "IndexMark", self.hwp.HParameterSet.HIndexMark.HSet
            )
            self.hwp.HParameterSet.HIndexMark.Key1 = keyword1
            self.hwp.HParameterSet.HIndexMark.Key2 = keyword2

            self.hwp.HAction.Execute(
                "IndexMark", self.hwp.HParameterSet.HIndexMark.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert index mark: {e}")
            return False

    def set_page_hiding(
        self,
        hide_header: bool = False,
        hide_footer: bool = False,
        hide_page_num: bool = False,
        hide_border: bool = False,
        hide_background: bool = False,
    ) -> bool:
        """Hide page elements (header, footer, etc.) for current page.

        Args:
            hide_header: Hide header
            hide_footer: Hide footer
            hide_page_num: Hide page number
            hide_border: Hide page border
            hide_background: Hide page background

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            self.hwp.HAction.GetDefault(
                "PageHiding", self.hwp.HParameterSet.HPageHiding.HSet
            )
            self.hwp.HParameterSet.HPageHiding.HideHeader = 1 if hide_header else 0
            self.hwp.HParameterSet.HPageHiding.HideFooter = 1 if hide_footer else 0
            self.hwp.HParameterSet.HPageHiding.HidePageNum = 1 if hide_page_num else 0
            self.hwp.HParameterSet.HPageHiding.HideBorder = 1 if hide_border else 0
            self.hwp.HParameterSet.HPageHiding.HideFill = 1 if hide_background else 0

            self.hwp.HAction.Execute(
                "PageHiding", self.hwp.HParameterSet.HPageHiding.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set page hiding: {e}")
            return False

    def insert_auto_number(
        self, num_type: str = "page", number_format: int = 0, new_number: int = 0
    ) -> bool:
        """Insert Auto Number (e.g., Figure 1, Table 1).

        Args:
            num_type: 'page', 'footnote', 'endnote', 'picture', 'table', 'equation'
            number_format: Number format code (0=Digit, 1=Circle, etc.)
            new_number: Reset to new number (0 to continue sequence)

        Returns:
            bool: Success status
        """
        if not self.is_document_open:
            return False

        try:
            # Map string types to HWP codes (Action: InsertAutoNum, Param: HAutoNum)
            code_map = {
                "page": 0,
                "footnote": 1,
                "endnote": 2,
                "picture": 3,
                "table": 4,
                "equation": 5,
            }

            if num_type.lower() not in code_map:
                logger.error(f"Invalid auto number type: {num_type}")
                return False

            self.hwp.HAction.GetDefault(
                "InsertAutoNum", self.hwp.HParameterSet.HAutoNum.HSet
            )
            self.hwp.HParameterSet.HAutoNum.NumType = code_map[num_type.lower()]
            self.hwp.HParameterSet.HAutoNum.Format = number_format
            self.hwp.HParameterSet.HAutoNum.NewNum = new_number

            self.hwp.HAction.Execute(
                "InsertAutoNum", self.hwp.HParameterSet.HAutoNum.HSet
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert auto number: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_document()
        self.quit()


# Global controller instance
_hwp_controller: Optional[WindowsHwpController] = None


def get_hwp_controller() -> Optional[WindowsHwpController]:
    """Get global HWP controller instance.

    Returns:
        WindowsHwpController: Controller instance (None on non-Windows)
    """
    global _hwp_controller
    if _hwp_controller is None:
        if IS_WINDOWS:
            _hwp_controller = WindowsHwpController()
        else:
            logger.warning("Cannot create HWP controller on non-Windows platform")
            return None
    return _hwp_controller


def reset_hwp_controller() -> None:
    """Reset global HWP controller instance."""
    global _hwp_controller
    if _hwp_controller:
        _hwp_controller.close_document()
        _hwp_controller.quit()
    _hwp_controller = None


def is_windows_platform() -> bool:
    """Check if running on Windows.

    Returns:
        bool: True if Windows
    """
    return IS_WINDOWS
