"""
Template Tools for HWP MCP Server
Unified template management for HWP (binary) and HWPX (XML)
"""

import os
import logging
from typing import Optional, Dict, Any, Callable, List

from src.tools.hwpx_template_engine import HwpxTemplateEngine

logger = logging.getLogger("hwp-mcp-extended.templates")

# Templates Storage (Sample)
DEFAULT_TEMPLATES = [
    {
        "id": "annual_leave",
        "name": "연차 사용 신청서",
        "category": "휴가",
        "description": "사원의 연차 사용을 신청하는 양식",
        "fields": [
            {"name": "employee_name", "label": "사원명", "type": "text"},
            {"name": "department", "label": "부서", "type": "text"},
            {"name": "position", "label": "직위", "type": "text"},
            {"name": "leave_start", "label": "휴가 시작일", "type": "date"},
            {"name": "leave_end", "label": "휴가 종료일", "type": "date"},
            {"name": "leave_type", "label": "휴가 종류", "type": "text"},
            {"name": "reason", "label": "사유", "type": "text"},
        ],
        "template_content": """{{employee_name}}님

{{department}} {{position}}

【휴가 신청】

▶ 휴가 기간: {{leave_start}} ~ {{leave_end}}
▶ 휴가 종류: {{leave_type}}
▶ 사유: {{reason}}
""",
    },
    # ... other templates ...
]

def register_template_tools(mcp, get_pyhwp_adapter: Callable) -> None:
    """Register template tools to MCP server"""

    _hwpx_engine = HwpxTemplateEngine()

    @mcp.tool()
    def hwp_create_from_template(
        template_id: str, data: Dict[str, Any], save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create document from template.
        Supports both built-in text templates and external .hwpx template files.
        
        Args:
            template_id: Template ID (built-in) or path to .hwpx file
            data: Data to fill
            save_path: Output path
        """
        try:
            # 1. External HWPX Template File
            if template_id.lower().endswith(".hwpx") and os.path.exists(template_id):
                if not save_path:
                    return {"status": "error", "error": "save_path is required for file templates"}
                
                # Use HWPX Engine
                result = _hwpx_engine.fill_template(template_id, save_path, data)
                return {
                    "status": "success",
                    "message": f"Created document from HWPX template: {save_path}",
                    "file_path": save_path
                }

            # 2. Built-in Text Template (Legacy)
            template = next((t for t in DEFAULT_TEMPLATES if t["id"] == template_id), None)
            
            if not template:
                return {
                    "status": "error",
                    "error": f"Template not found: {template_id}",
                }

            # Use simple text replacement for built-in templates
            content = template.get("template_content", "")
            for key, value in data.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))

            saved_path = None
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_path = save_path

            return {
                "status": "success",
                "template_id": template_id,
                "filled_content": content,
                "saved_path": saved_path,
            }

        except Exception as e:
            logger.error(f"Error creating from template: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_list_templates() -> Dict[str, Any]:
        """List all available built-in templates"""
        return {
            "status": "success",
            "templates": DEFAULT_TEMPLATES,
            "count": len(DEFAULT_TEMPLATES)
        }

    # Re-export engine methods for explicit usage
    @mcp.tool()
    def hwp_analyze_template_file(file_path: str) -> Dict[str, Any]:
        """Analyze a .hwpx template file to find placeholders."""
        return _hwpx_engine.analyze_template(file_path)

    @mcp.tool()
    def hwp_fill_template_file(
        template_path: str, output_path: str, data: Dict[str, str]
    ) -> Dict[str, Any]:
        """Explicitly fill a .hwpx file (alias for create_from_template with file path)."""
        return hwp_create_from_template(template_path, data, output_path)
