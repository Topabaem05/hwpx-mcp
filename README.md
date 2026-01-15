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

## Available Tools

### System & Connection

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_connect` | Connect to HWP controller (auto-selects Windows COM or cross-platform) | All |
| `hwp_disconnect` | Disconnect from HWP controller and release resources | All |
| `hwp_platform_info` | Get current platform information and available HWP capabilities | All |
| `hwp_capabilities` | Get the full capability matrix showing what's supported | All |

### Document Lifecycle

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create` | Create a new HWP document | All |
| `hwp_open` | Open an existing HWP/HWPX document | All |
| `hwp_save` | Save the current document | All |
| `hwp_save_as` | Save document in specified format (hwp, hwpx, pdf) | All |
| `hwp_close` | Close the current document | All |

### Text & Editing

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_insert_text` | Insert text at current cursor position | All |
| `hwp_get_text` | Get all text from the current document | All |
| `hwp_find` | Find text in the document | All |
| `hwp_find_replace` | Find and replace text (1 occurrence) | Windows |
| `hwp_find_replace_all` | Find and replace all occurrences | Windows |
| `hwp_find_advanced` | Advanced find with regex support | Windows |
| `hwp_find_replace_advanced` | Advanced find/replace with regex | Windows |

### Table Operations

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create_table` | Create a table with specified rows and columns | All |
| `hwp_set_cell_text` | Set text in a specific cell (row, col) | All |
| `hwp_get_cell_text` | Get text from a specific cell | All |
| `hwp_goto_cell` | Go to a specific cell address (e.g., 'A1') | Windows |
| `hwp_get_cell_addr` | Get current cell address (e.g., 'A1') | Windows |
| `hwp_adjust_cellwidth` | Adjust column widths (ratio mode supported) | Windows |

### Formatting

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_set_font` | Set font name and size | All |
| `hwp_set_charshape` | Set character shape (bold, italic, underline, color) | Windows |
| `hwp_get_charshape` | Get current character shape info | Windows |
| `hwp_set_parashape` | Set paragraph shape (alignment, line spacing) | Windows |
| `hwp_toggle_bold` | Toggle bold formatting | Windows |
| `hwp_toggle_italic` | Toggle italic formatting | Windows |
| `hwp_toggle_underline` | Toggle underline formatting | Windows |
| `hwp_toggle_strikethrough` | Toggle strikethrough formatting | Windows |

### Charts

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create_chart` | Create a chart with data | All |

### Equations

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create_equation` | Create a mathematical equation | All |

### Templates

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_create_from_template` | Create document from template file | All |
| `hwp_fill_template` | Fill template fields with data | All |

### Fields (Click-Here Fields)

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_get_field_list` | Get list of all field names | Windows |
| `hwp_put_field_text` | Set text in a field by name | Windows |
| `hwp_get_field_text` | Get text from a field | Windows |
| `hwp_field_exists` | Check if a field exists | Windows |
| `hwp_create_field` | Create a new field | Windows |

### Page & Navigation

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_get_page_count` | Get total page count | All |
| `hwp_goto_page` | Go to specific page (0-based) | All |
| `hwp_move_to_start` | Move cursor to document start | Windows |
| `hwp_move_to_end` | Move cursor to document end | Windows |
| `hwp_get_page_text` | Get text from a specific page | Windows |

### Utility Tools

| Tool | Description | Platform |
|------|-------------|----------|
| `hwp_head_type` | Convert heading type string to HWP integer value | All |
| `hwp_line_type` | Convert line type string to HWP integer value | All |
| `hwp_line_width` | Convert line width string to HWP integer value | All |
| `hwp_number_format` | Convert number format string to HWP integer | All |
| `hwp_convert_unit` | Convert between HwpUnit and millimeters | All |
| `hwp_get_head_types` | Get available heading types | All |
| `hwp_get_line_types` | Get available line types | All |
| `hwp_get_line_widths` | Get available line widths | All |
| `hwp_get_number_formats` | Get available number formats | All |

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

## Roadmap & Planned Features

We plan to expand the capabilities of HWPX-MCP by referencing [Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server) and utilizing the advanced automation features of [pyhwpx](https://github.com/martiniifun/pyhwpx) (based on [pywin32](https://github.com/mhammond/pywin32)).

### Phase 1: Advanced Formatting & Styles
| Feature | Description | Priority |
|---------|-------------|----------|
| **Paragraph Styles** | Indentation, line spacing, alignment, tab settings | High |
| **Character Styles** | Font families, sizing, colors, highlights, spacing | High |
| **Style Management** | Apply/manage named styles (e.g., "제목 1", "본문") | Medium |
| **Direct Formatting** | Font/size/bold/italic during content creation | High |

### Phase 2: Page Layout & Sections
| Feature | Description | Priority |
|---------|-------------|----------|
| **Page Setup** | Orientation (Portrait/Landscape), margins, paper size | High |
| **Multi-Column** | Create and manage multi-column layouts | Medium |
| **Headers & Footers** | Edit header/footer content, page numbering | High |
| **Section Control** | Manage sections with distinct layouts | Medium |

### Phase 3: Advanced Table Operations
| Feature | Description | Priority |
|---------|-------------|----------|
| **Cell Merging** | Horizontal, vertical, and rectangular merging | High |
| **Cell Alignment** | Horizontal and vertical positioning | High |
| **Cell Padding** | Independent control of all sides | Medium |
| **Column Width** | Points, percentage, auto-fit | Medium |
| **Alternating Rows** | Apply alternating row colors | Low |
| **Header Highlighting** | Custom header row colors | Low |

### Phase 4: Advanced Objects & Media
| Feature | Description | Priority |
|---------|-------------|----------|
| **Images** | Precise sizing, positioning, wrapping styles | High |
| **Shapes & Text Boxes** | Insert/format geometric shapes, floating text boxes | Medium |
| **Hyperlinks** | Internal bookmarks, external hyperlinks | Medium |
| **OLE Objects** | Embed external objects | Low |

### Phase 5: Review & Collaboration (Windows Only)
| Feature | Description | Priority |
|---------|-------------|----------|
| **Comments** | Insert, read, delete document comments | High |
| **Track Changes** | Enable/disable revision tracking, accept/reject | Medium |
| **Document Protection** | Password protection, restricted editing | Low |

### Phase 6: Document Automation
| Feature | Description | Priority |
|---------|-------------|----------|
| **Mail Merge** | Enhanced field mapping, batch generation | Medium |
| **Table of Contents** | Auto-generate/update TOC based on headings | High |
| **Index** | Create index entries and generate pages | Low |
| **PDF Conversion** | Convert HWP/HWPX to PDF | High |
| **Document Merging** | Merge multiple documents | Medium |

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
