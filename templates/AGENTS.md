# templates/

## Overview
Built-in HWPX templates shipped with the project, plus a manifest (`template_index.json`) for IDs/metadata.

## Structure
```
templates/
├── template_index.json           # template catalog (IDs, filenames, categories, keywords)
├── h01/..h06/                    # per-template docs + preview images
└── *.hwpx                        # built-in HWPX template files
```

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Template catalog | `templates/template_index.json` | source of truth for template IDs/metadata
| Template filling | `hwpx_mcp/tools/template_tools.py` | `hwp_create_from_template` chooses file vs built-in
| HWPX fill engine | `hwpx_mcp/tools/hwpx_template_engine.py` | `HwpxDocument.replace_text_in_runs`

## Conventions
- Template IDs in `templates/template_index.json` map to `.hwpx` filenames.
- Placeholders:
  - HWPX file templates: replaced via `replace_text_in_runs()`.
  - Text templates (in code): mustache-style `{{key}}` replacement.

## Anti-Patterns
- Don’t rely on Windows-only features inside templates; templates must work in Docker/Linux (HWPX creation path).
