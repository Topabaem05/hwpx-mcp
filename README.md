# HWPX-MCP

**[English](README.md) | [한국어](README.kr.md)**

A Model Context Protocol (MCP) server for creating and editing HWP/HWPX documents. This server provides AI assistants (like Claude, Cursor) with the ability to programmatically create, edit, and manipulate Hangul (Korean word processor) documents.

## Features

- **Cross-Platform Support**: Works on Windows (via COM Automation) and macOS/Linux (via python-hwpx)
- **120+ MCP Tools**: Comprehensive set of tools for document manipulation
- **Template Support**: Create documents from templates with field substitution
- **Chart Creation**: Insert and configure charts in documents
- **Equation Support**: Insert mathematical equations (LaTeX/Script)
- **Table Operations**: Full table manipulation (create, edit, format)
- **Formatting Control**: Character and paragraph formatting

## Quick Start (Copy & Paste)

### 1. Install

<details>
<summary><b>Using uv (recommended)</b></summary>

```bash
git clone https://github.com/Topabaem05/hwpx-mcp.git
cd hwpx-mcp && uv pip install -e .
```

</details>

<details>
<summary><b>Using Anaconda/Conda</b></summary>

```bash
git clone https://github.com/Topabaem05/hwpx-mcp.git
cd hwpx-mcp
conda create -n hwpx-mcp python=3.11 -y
conda activate hwpx-mcp
pip install -e .
```

</details>

### 2. Get Your Install Path

Run this in the `hwpx-mcp` directory to copy the path:

```bash
# macOS/Linux
pwd | pbcopy  # macOS (copies to clipboard)
pwd           # Linux (copy manually)

# Windows (PowerShell)
(Get-Location).Path | clip
```

**For Anaconda users**, also get your Python path:

```bash
# macOS/Linux
which python | pbcopy  # After: conda activate hwpx-mcp

# Windows (PowerShell)
(Get-Command python).Source | clip
```

### 3. Configure Your MCP Client

Use the path from step 2 in the config below:

<details>
<summary><b>Claude Desktop (macOS) - uv</b></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "uv",
      "args": ["--directory", "/PASTE/YOUR/PATH/HERE", "run", "hwpx-mcp"]
    }
  }
}
```

</details>

<details>
<summary><b>Claude Desktop (macOS) - Anaconda</b></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "/PASTE/YOUR/CONDA/PYTHON/PATH/HERE",
      "args": ["-m", "hwpx_mcp.server"],
      "cwd": "/PASTE/YOUR/HWPX-MCP/PATH/HERE"
    }
  }
}
```

> Example paths:
> - Python: `/Users/username/anaconda3/envs/hwpx-mcp/bin/python`
> - cwd: `/Users/username/projects/hwpx-mcp`

</details>

<details>
<summary><b>Claude Desktop (Windows) - uv</b></summary>

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "cmd",
      "args": ["/c", "uv --directory C:\\PASTE\\YOUR\\PATH\\HERE run hwpx-mcp"]
    }
  }
}
```

</details>

<details>
<summary><b>Claude Desktop (Windows) - Anaconda</b></summary>

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "C:\\PASTE\\YOUR\\CONDA\\PYTHON\\PATH\\HERE\\python.exe",
      "args": ["-m", "hwpx_mcp.server"],
      "cwd": "C:\\PASTE\\YOUR\\HWPX-MCP\\PATH\\HERE"
    }
  }
}
```

> Example paths:
> - Python: `C:\Users\username\anaconda3\envs\hwpx-mcp\python.exe`
> - cwd: `C:\Users\username\projects\hwpx-mcp`

</details>

<details>
<summary><b>Claude Desktop (Linux) - uv</b></summary>

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "uv",
      "args": ["--directory", "/PASTE/YOUR/PATH/HERE", "run", "hwpx-mcp"]
    }
  }
}
```

</details>

<details>
<summary><b>Claude Desktop (Linux) - Anaconda</b></summary>

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "/PASTE/YOUR/CONDA/PYTHON/PATH/HERE",
      "args": ["-m", "hwpx_mcp.server"],
      "cwd": "/PASTE/YOUR/HWPX-MCP/PATH/HERE"
    }
  }
}
```

> Example paths:
> - Python: `/home/username/anaconda3/envs/hwpx-mcp/bin/python`
> - cwd: `/home/username/projects/hwpx-mcp`

</details>

<details>
<summary><b>Cursor - uv</b></summary>

Edit `~/.cursor/mcp.json` (macOS/Linux) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "uv",
      "args": ["--directory", "/PASTE/YOUR/PATH/HERE", "run", "hwpx-mcp"]
    }
  }
}
```

</details>

<details>
<summary><b>Cursor - Anaconda</b></summary>

Edit `~/.cursor/mcp.json` (macOS/Linux) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "hwpx-mcp": {
      "command": "/PASTE/YOUR/CONDA/PYTHON/PATH/HERE",
      "args": ["-m", "hwpx_mcp.server"],
      "cwd": "/PASTE/YOUR/HWPX-MCP/PATH/HERE"
    }
  }
}
```

</details>

<details>
<summary><b>VS Code (Copilot) - uv</b></summary>

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "hwpx-mcp": {
        "command": "uv",
        "args": ["--directory", "/PASTE/YOUR/PATH/HERE", "run", "hwpx-mcp"]
      }
    }
  }
}
```

</details>

<details>
<summary><b>VS Code (Copilot) - Anaconda</b></summary>

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "hwpx-mcp": {
        "command": "/PASTE/YOUR/CONDA/PYTHON/PATH/HERE",
        "args": ["-m", "hwpx_mcp.server"],
        "cwd": "/PASTE/YOUR/HWPX-MCP/PATH/HERE"
      }
    }
  }
}
```

</details>

<details>
<summary><b>OpenCode - uv</b></summary>

Create or edit `opencode.json` in your project root (or `~/.config/opencode/opencode.json` for global config):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "hwpx-mcp": {
      "type": "local",
      "command": ["uv", "--directory", "/PASTE/YOUR/PATH/HERE", "run", "hwpx-mcp"],
      "enabled": true
    }
  }
}
```

</details>

<details>
<summary><b>OpenCode - Anaconda</b></summary>

Create or edit `opencode.json` in your project root (or `~/.config/opencode/opencode.json` for global config):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "hwpx-mcp": {
      "type": "local",
      "command": ["/PASTE/YOUR/CONDA/PYTHON/PATH/HERE", "-m", "hwpx_mcp.server"],
      "enabled": true,
      "environment": {
        "PYTHONPATH": "/PASTE/YOUR/HWPX-MCP/PATH/HERE"
      }
    }
  }
}
```

> Example paths:
> - Python: `/Users/username/anaconda3/envs/hwpx-mcp/bin/python` (macOS/Linux)
> - Python: `C:\\Users\\username\\anaconda3\\envs\\hwpx-mcp\\python.exe` (Windows)
> - PYTHONPATH: `/Users/username/projects/hwpx-mcp`

</details>

### 4. Restart your MCP client and start using HWP tools!

## Tool Reference

### 1. Document Management
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_connect` | Connect to HWP controller (auto-selects Windows COM or cross-platform) | All |
| `hwp_create` | Create a new HWP document | All |
| `hwp_open` | Open an existing HWP/HWPX document | All |
| `hwp_save` | Save the current document | All |
| `hwp_save_as` | Save document in specified format (hwp, hwpx, pdf) | All |
| `hwp_close` | Close the current document | All |
| `hwp_disconnect` | Disconnect from HWP controller | All |
| `hwp_set_edit_mode` | Set document mode (edit, readonly, form) | Windows |

### 2. Text & Formatting
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_insert_text` | Insert text at current cursor position | All |
| `hwp_get_text` | Get all text from the current document | All |
| `hwp_set_font` | Set font name and size | All |
| `hwp_set_charshape` | Set character shape (bold, italic, underline, color) | Windows |
| `hwp_get_charshape` | Get current character shape info | Windows |
| `hwp_set_parashape` | Set paragraph shape (alignment, line spacing) | Windows |
| `hwp_toggle_bold` | Toggle bold formatting | Windows |
| `hwp_toggle_italic` | Toggle italic formatting | Windows |
| `hwp_toggle_underline` | Toggle underline formatting | Windows |
| `hwp_toggle_strikethrough` | Toggle strikethrough formatting | Windows |
| `hwp_insert_dutmal` | Insert Dutmal (text with comment above/below) | Windows |

### 3. Tables
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create_table` | Create a table with specified rows and columns | All |
| `hwp_set_cell_text` | Set text in a specific cell (row, col) | All |
| `hwp_get_cell_text` | Get text from a specific cell | All |
| `hwp_table_format_cell` | Format table cells (border type/width, fill color) | Windows |
| `hwp_table_split_cell` | Split current table cell into rows and columns | Windows |
| `hwp_table_merge_cells` | Merge selected table cells | Windows |
| `hwp_goto_cell` | Go to a specific cell address (e.g., 'A1') | Windows |
| `hwp_get_cell_addr` | Get current cell address (e.g., 'A1') | Windows |
| `hwp_adjust_cellwidth` | Adjust column widths (ratio mode supported) | Windows |

### 4. Page & Layout
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_page_setup` | Set page layout (margins, orientation, paper size) | Windows |
| `hwp_setup_columns` | Configure page columns (count, same size, gap) | Windows |
| `hwp_insert_page_number` | Insert page numbering with position/format | Windows |
| `hwp_insert_header_footer` | Insert header or footer with text content | Windows |
| `hwp_set_page_hiding` | Hide page elements (header, footer, page num, etc.) | Windows |
| `hwp_break_page` | Insert a page break | Windows |
| `hwp_break_section` | Insert a section break | Windows |
| `hwp_get_page_count` | Get total page count | All |
| `hwp_goto_page` | Go to specific page (0-based) | All |

### 5. Navigation & Selection
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_move_to` | Precise cursor movement (37+ targets: Main, CurList, Cells, etc.) | Windows |
| `hwp_select_range` | Select text range by paragraph and position indices | Windows |
| `hwp_insert_bookmark` | Insert bookmark at cursor position | Windows |
| `hwp_move_to_start` | Move cursor to document start | Windows |
| `hwp_move_to_end` | Move cursor to document end | Windows |
| `hwp_find` | Find text in the document | All |
| `hwp_find_replace` | Find and replace text (1 occurrence) | Windows |
| `hwp_find_replace_all` | Find and replace all occurrences | Windows |
| `hwp_find_advanced` | Advanced find with regex support | Windows |

### 6. Objects & Inserts
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_insert_picture` | Insert an image at current cursor position | All |
| `hwp_insert_background` | Insert background image (tile, center, stretch) | Windows |
| `hwp_insert_hyperlink` | Insert hyperlink at cursor position | Windows |
| `hwp_insert_note` | Insert footnote or endnote | Windows |
| `hwp_insert_index_mark` | Insert Index Mark (keyword1, keyword2) | Windows |
| `hwp_insert_auto_number` | Insert Auto Number (Page, Figure, Table, etc.) | Windows |

### 10. XML Processing & Security
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_xml_validate_content` | Validate HWPX XML syntax/schema | All |
| `hwp_xml_xpath_query` | Execute XPath on HWPX XML (hp: namespaces) | All |
| `hwp_xml_parse_section` | Parse Section XML into structured JSON | All |
| `hwp_smart_patch_xml` | Validate and patch HWPX XML with smart filtering | All |

### 11. Conversion & Export
| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_convert_format` | Convert between HWP, HWPX, PDF, HTML | Windows |
| `hwp_export_pdf` | Export to PDF | Windows |
| `hwp_export_html` | Export to HTML | Windows |

## Usage Examples

### Basic Document Creation

```python
# Connect to HWP
hwp_connect(visible=True)

# Create a new document
hwp_create()

# Set font and insert text
hwp_set_font(font_name="NanumGothic", size=12)
hwp_insert_text("Hello, HWP MCP!")

# Save the document
hwp_save_as(path="output.hwpx", format="hwpx")
hwp_disconnect()
```

### Creating a Table

```python
hwp_connect()
hwp_create()

# Create a 3x2 table
hwp_create_table(rows=3, cols=2)

# Fill header row
hwp_set_cell_text(row=0, col=0, text="Name")
hwp_set_cell_text(row=0, col=1, text="Value")

# Fill data
hwp_set_cell_text(row=1, col=0, text="Item 1")
hwp_set_cell_text(row=1, col=1, text="100")
hwp_set_cell_text(row=2, col=0, text="Item 2")
hwp_set_cell_text(row=2, col=1, text="200")

# Save
hwp_save_as(path="table_example.hwpx")
```

### Using Templates

```python
hwp_connect()
hwp_open(path="template.hwpx")

# Fill fields
hwp_put_field_text(name="title", text="My Document Title")
hwp_put_field_text(name="author", text="John Doe")
hwp_put_field_text(name="date", text="2024-01-15")

# Save as new document
hwp_save_as(path="filled_document.hwpx")
```

### Finding and Replacing Text

```python
hwp_connect()
hwp_open(path="document.hwpx")

# Find text
result = hwp_find(text="old text")
if result["found"]:
    print("Text found!")

# Replace all occurrences
result = hwp_find_replace_all(find_text="old", replace_text="new")
print(f"Replaced {result['count']} occurrences")

# Advanced replace with regex
result = hwp_find_replace_all_advanced(
    find_text=r"\d+",  # Match numbers
    replace_text="[NUMBER]",
    regex=True
)
```

### Formatting Text

```python
hwp_connect()
hwp_create()

# Set font
hwp_set_font(font_name="NanumGothic", size=16, bold=True)

# Insert title
hwp_insert_text("Document Title\n\n")

# Reset formatting
hwp_set_font(font_name="NanumGothic", size=12)

# Insert body
hwp_insert_text("This is the body text.")

# Toggle bold on selection
hwp_toggle_bold()
```

### HWP SDK Extended Features (Windows)

```python
hwp_connect()
hwp_create()

# Execute any action from Actions.h (800+ available)
hwp_run_action(action_id="CharShapeBold")  # Toggle bold
hwp_run_action(action_id="ParagraphShapeAlignCenter")  # Center align

# Page setup (A4, Letter, margins, orientation)
hwp_page_setup(
    paper_type="a4",
    orientation="portrait",
    top_margin_mm=25,
    bottom_margin_mm=25,
    left_margin_mm=30,
    right_margin_mm=30
)

# Insert page numbering
hwp_insert_page_number(
    position=4,  # 4=BottomCenter
    number_format=0,  # 0=Arabic (1, 2, 3...)
    starting_number=1,
    side_char="-"  # Results in "- 1 -"
)

# Format table cells (select cells first)
hwp_table_format_cell(
    fill_color=0xFFFF00,  # Yellow
    border_type=1,  # Solid
    border_width=5  # 0.5mm
)

# Precise cursor navigation
hwp_move_to(move_id="MoveDocEnd")  # Go to document end
hwp_move_to(move_id="MoveParaBegin")  # Go to paragraph start

# Select text range
hwp_select_range(
    start_para=0, start_pos=0,
    end_para=0, end_pos=10
)

# Insert header/footer
hwp_insert_header_footer(
    header_or_footer="header",
    content="Company Name - Confidential"
)

# Insert footnote
hwp_insert_note(
    note_type="footnote",
    content="Reference: HWP SDK Documentation"
)

# Set document mode
hwp_set_edit_mode(mode="readonly")  # readonly, edit, form

# Manage metatags (hidden metadata)
hwp_manage_metatags(action="set", tag_name="author", tag_value="AI Assistant")
hwp_manage_metatags(action="list")  # Get all tags

# Insert background image
hwp_insert_background(
    image_path="background.png",
    embedded=True,
    fill_option="tile"  # tile, center, stretch, fit
)

# Insert bookmark and hyperlink
hwp_insert_bookmark(name="section1")
hwp_insert_hyperlink(url="https://example.com", display_text="Visit Website")

# Table operations (split/merge)
# Assume cursor is in a table cell
hwp_table_split_cell(rows=2, cols=2)

# Assume cells are selected
hwp_table_merge_cells()

hwp_save_as(path="advanced_document.hwp")
```

### Advanced Automation Scenario

This example demonstrates how to combine multiple features to create a structured report.

```python
hwp_connect()
hwp_create()

# 1. Setup Page
hwp_page_setup(paper_type="a4", orientation="portrait", top_margin_mm=20)

# 2. Add Title with Bookmark
hwp_set_font(font_name="Malgun Gothic", size=24, bold=True)
hwp_insert_text("Monthly Report\n")
hwp_insert_bookmark(name="top")  # Bookmark for navigation
hwp_insert_text("\n")

# 3. Add Summary Section
hwp_set_font(font_name="Malgun Gothic", size=14, bold=True)
hwp_insert_text("1. Summary\n")
hwp_set_font(font_name="Malgun Gothic", size=11, bold=False)
hwp_insert_text("This report summarizes the key performance indicators.\n")
hwp_insert_text("For more details, visit our ")
hwp_insert_hyperlink(url="https://dashboard.example.com", display_text="Dashboard")
hwp_insert_text(".\n\n")

# 4. Create Data Table
hwp_set_font(font_name="Malgun Gothic", size=14, bold=True)
hwp_insert_text("2. Data Table\n")
hwp_create_table(rows=4, cols=3)

# Header
hwp_set_cell_text(row=0, col=0, text="Metric")
hwp_set_cell_text(row=0, col=1, text="Target")
hwp_set_cell_text(row=0, col=2, text="Actual")

# Format Header (Yellow background)
# Note: Requires navigating to each cell
hwp_goto_cell("A1")
hwp_table_format_cell(fill_color=0xFFFF00)
hwp_goto_cell("B1")
hwp_table_format_cell(fill_color=0xFFFF00)
hwp_goto_cell("C1")
hwp_table_format_cell(fill_color=0xFFFF00)

# 5. Split a cell for detailed notes
hwp_move_to(move_id="MoveDocEnd")
hwp_insert_text("\n\nNotes:\n")
hwp_create_table(rows=1, cols=1)
hwp_table_split_cell(rows=2, cols=1)  # Split single cell into two rows
hwp_set_cell_text(row=0, col=0, text="Note 1: Market conditions stable.")
hwp_set_cell_text(row=1, col=0, text="Note 2: Q3 projections updated.")

# 6. Add Footer
hwp_insert_header_footer(header_or_footer="footer", content="Confidential - Internal Use Only")

hwp_save_as("monthly_report.hwp")
```

## Platform Differences

| Feature | Windows (COM) | macOS/Linux (python-hwpx) |
|---------|---------------|---------------------------|
| Edit existing HWP | ✅ Full support | ❌ Read-only |
| Create new HWPX | ✅ Full support | ✅ Full support |
| Tables | ✅ All features | ✅ Basic features |
| Charts | ✅ All features | ✅ Creation only |
| Equations | ✅ All features | ✅ Creation only |
| Fields | ✅ Full support | ❌ Not supported |
| Formatting | ✅ Full control | ✅ Basic control |
| SDK Extended (Actions, PageSetup, etc.) | ✅ Full support | ❌ Not supported |

## Requirements

- Python 3.10+
- MCP >= 1.0.0
- fastmcp >= 0.2.0
- pyhwp >= 0.1a (for HWP reading on non-Windows)
- python-hwpx >= 1.9 (for HWPX creation)
- pandas >= 2.0.0 (for chart data)
- matplotlib >= 3.7.0 (for chart rendering)

### Windows Only
- pywin32 >= 300 (for COM automation)
- Hancom Office 2010 or later

## Architecture

```
┌─────────────────────────────────────────────────┐
│              MCP Client (Claude, etc.)           │
└───────────────────┬─────────────────────────────┘
                    │ JSON-RPC
                    ▼
┌─────────────────────────────────────────────────┐
│              HWPX-MCP Server                     │
│              (src/server.py)                     │
└───────────────────┬─────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌─────────────────┐  ┌─────────────────────┐
│ Windows HWP     │  │ Cross-Platform HWPX │
│ Controller      │  │ Controller          │
│ (pywin32/COM)   │  │ (python-hwpx)       │
└─────────────────┘  └─────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────┐  ┌─────────────────────┐
│ Hancom Office   │  │ HWPX File Generation│
│ (Windows only)  │  │ (Headless)          │
└─────────────────┘  └─────────────────────┘
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest hwpx_mcp/tests/ -v

# Run the server
python -m hwpx_mcp.server
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## References

This project was inspired and referenced by the following excellent libraries and MCP servers:

### MCP Servers
- **[Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server)** - MCP server for Microsoft Word. We reference its comprehensive tool design (document management, content creation, table formatting, comments) to provide a comparable experience for HWP documents.

### HWP Automation Libraries
- **[pyhwpx](https://github.com/martiniifun/pyhwpx)** - A comprehensive Python wrapper for HWP automation (Windows). Built on pywin32, it provides high-level APIs for text insertion, document editing, formatting, tables, and more. Key reference for implementing advanced features.
- **[pywin32](https://github.com/mhammond/pywin32)** - Python for Windows extensions providing access to Windows APIs including COM automation. The foundation for Windows HWP automation via `win32com`.
- **[python-hwpx](https://github.com/airmang/python-hwpx)** - Python library for HWPX (Open XML) file manipulation. Used for cross-platform HWPX generation without requiring HWP installation.

### HWP File Format Libraries
- **[hwplibsharp](https://github.com/rkttu/hwplibsharp)** - C# library for HWP file format parsing.
- **[hwplib](https://github.com/neolord0/hwplib)** - Java library for HWP file format.
- **[pyhwp](https://github.com/mete0r/pyhwp)** - Python tools for parsing HWP binary files.

### Previous Work
- **[hwp-mcp](https://github.com/jkf87/hwp-mcp)** - The original MCP server for HWP documents that inspired this extended version.

Special thanks to the developers of these projects for their contributions to the HWP ecosystem.
