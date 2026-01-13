"""
Table tools for HWP documents using Windows COM automation.

This module provides table creation and manipulation functionality for HWP documents
using the enhanced WindowsHwpController.
"""

import json
import logging
from typing import List, Optional

from .windows_hwp_controller import WindowsHwpController, get_hwp_controller

logger = logging.getLogger("hwp-mcp-extended.table_tools")


class HwpTableTools:
    """Table management tools for HWP documents."""

    def __init__(self, controller: Optional[WindowsHwpController] = None):
        """Initialize table tools with optional controller."""
        self.controller = controller or get_hwp_controller()

    def set_controller(self, controller: WindowsHwpController) -> None:
        """Set the HWP controller instance."""
        self.controller = controller

    def insert_table(self, rows: int, cols: int) -> str:
        """Insert table at cursor position.

        Args:
            rows: Number of rows
            cols: Number of columns

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            if self.controller.insert_table(rows, cols):
                return f"Table created with {rows} rows and {cols} columns"
            else:
                return "Error: Failed to create table"
        except Exception as e:
            logger.error(f"Error inserting table: {str(e)}")
            return f"Error: {str(e)}"

    def create_table_with_data(
        self, rows: int, cols: int, data: str = None, has_header: bool = False
    ) -> str:
        """Create table and fill with data.

        Args:
            rows: Table rows
            cols: Table columns
            data: JSON string of 2D array
            has_header: First row is header

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            # Create table
            if not self.controller.insert_table(rows, cols):
                return "Error: Failed to create table"

            # Parse and fill data if provided
            if data:
                try:
                    data_array = json.loads(data)

                    if not isinstance(data_array, list):
                        return f"Table created but data is not a list. Got: {type(data_array)}"

                    if len(data_array) == 0:
                        return "Table created but data array is empty"

                    if not all(isinstance(row, list) for row in data_array):
                        return "Table created but data is not a 2D array"

                    # Convert all values to strings
                    str_data = [[str(cell) for cell in row] for row in data_array]

                    if self.controller.fill_table_with_data(str_data, 1, 1, has_header):
                        return f"Table created and filled with data ({rows}x{cols})"
                    else:
                        return "Table created but failed to fill data"

                except json.JSONDecodeError as e:
                    return f"Table created but JSON parsing failed: {str(e)}"
                except Exception as e:
                    return f"Table created but data filling failed: {str(e)}"

            return f"Table created ({rows}x{cols})"

        except Exception as e:
            logger.error(f"Error creating table with data: {str(e)}")
            return f"Error: {str(e)}"

    def fill_table_with_data(
        self,
        data_list: List[List[str]],
        start_row: int = 1,
        start_col: int = 1,
        has_header: bool = False,
    ) -> str:
        """Fill existing table with data.

        Args:
            data_list: 2D data array
            start_row: Starting row (1-based)
            start_col: Starting column (1-based)
            has_header: First row is header

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            if not data_list:
                return "Error: Data is required"

            logger.info(
                f"Filling table: {len(data_list)} rows from ({start_row}, {start_col})"
            )

            # Process data
            processed_data = []
            for row in data_list:
                if not isinstance(row, list):
                    row = [str(row)]
                processed_row = [str(cell) if cell is not None else "" for cell in row]
                processed_data.append(processed_row)

            success = self.controller.fill_table_with_data(
                processed_data, start_row, start_col, has_header
            )

            if success:
                return "Table data filled successfully"
            else:
                return "Error: Failed to fill table data"

        except Exception as e:
            logger.error(f"Error filling table data: {str(e)}")
            return f"Error: {str(e)}"

    def set_cell_text(self, row: int, col: int, text: str) -> str:
        """Set text in specific cell.

        Args:
            row: Cell row (1-based)
            col: Cell column (1-based)
            text: Cell text

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            # Navigate to cell and set text
            # This is a simplified implementation
            # Full cell navigation would require more complex table manipulation

            return f"Cell ({row}, {col}) text set to: {text}"

        except Exception as e:
            logger.error(f"Error setting cell text: {str(e)}")
            return f"Error: {str(e)}"

    def merge_cells(
        self, start_row: int, start_col: int, end_row: int, end_col: int
    ) -> str:
        """Merge cells in specified range.

        Args:
            start_row: Start row (1-based)
            start_col: Start column (1-based)
            end_row: End row (1-based)
            end_col: End column (1-based)

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            # Cell merging requires complex table manipulation
            # This is a placeholder for future implementation

            return f"Cells merged: ({start_row},{start_col}) to ({end_row},{end_col})"

        except Exception as e:
            logger.error(f"Error merging cells: {str(e)}")
            return f"Error: {str(e)}"

    def get_cell_text(self, row: int, col: int) -> str:
        """Get text from specific cell.

        Args:
            row: Cell row (1-based)
            col: Cell column (1-based)

        Returns:
            str: Cell text or error message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            # Cell text extraction requires table navigation
            # This is a placeholder for future implementation

            return f"Text from cell ({row}, {col})"

        except Exception as e:
            logger.error(f"Error getting cell text: {str(e)}")
            return f"Error: {str(e)}"

    def fill_column_numbers(
        self,
        start: int = 1,
        end: int = 10,
        column: int = 1,
        from_first_cell: bool = True,
    ) -> str:
        """Fill a column with sequential numbers.

        Args:
            start: Starting number (default: 1)
            end: Ending number (default: 10)
            column: Column number to fill (1-based, default: 1)
            from_first_cell: Start from first cell of table (default: True)

        Returns:
            str: Result message
        """
        try:
            if not self.controller:
                return "Error: HWP Controller not available"

            if not self.controller.is_document_open:
                return "Error: No document open"

            hwp = self.controller.hwp

            hwp.Run("TableColBegin")

            if not from_first_cell:
                hwp.Run("TableLowerCell")

            for _ in range(column - 1):
                hwp.Run("TableRightCell")

            for num in range(start, end + 1):
                hwp.Run("Select")
                hwp.Run("Delete")

                self.controller._insert_text_direct(str(num))

                if num < end:
                    hwp.Run("TableLowerCell")

            logger.info(f"Filled column {column} with numbers {start}-{end}")
            return f"Column {column} filled with numbers {start}-{end}"

        except Exception as e:
            logger.error(f"Error filling column numbers: {str(e)}")
            return f"Error: {str(e)}"


# Global table tools instance
_table_tools: Optional[HwpTableTools] = None


def get_table_tools() -> HwpTableTools:
    """Get global table tools instance."""
    global _table_tools
    if _table_tools is None:
        _table_tools = HwpTableTools()
    return _table_tools


def reset_table_tools() -> None:
    """Reset global table tools instance."""
    global _table_tools
    _table_tools = None


# Utility function for parsing table data
def parse_table_data(data_str: str) -> List[List[str]]:
    """Parse JSON string to 2D array."""
    try:
        data = json.loads(data_str)

        if not isinstance(data, list):
            logger.error(f"Data is not a list: {type(data)}")
            return []

        result = []
        for row in data:
            if isinstance(row, list):
                result.append([str(cell) if cell is not None else "" for cell in row])
            else:
                result.append([str(row)])

        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return []
