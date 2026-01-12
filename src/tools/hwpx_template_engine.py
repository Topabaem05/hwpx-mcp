"""
HWPX Template Engine
Analyzes and fills HWPX templates using python-hwpx library.
"""

import os
import logging
from typing import Dict, Any, List
try:
    from hwpx.document import HwpxDocument
    from hwpx.tools.text_extractor import TextExtractor
    HAS_PYTHON_HWPX = True
except ImportError:
    HAS_PYTHON_HWPX = False

logger = logging.getLogger("hwp-mcp-extended.template_engine")

class HwpxTemplateEngine:
    def __init__(self):
        if not HAS_PYTHON_HWPX:
            logger.warning("python-hwpx not installed. HWPX templating will be unavailable.")

    def analyze_template(self, hwpx_path: str) -> Dict[str, Any]:
        """
        Analyze HWPX file and return structure information using TextExtractor.
        """
        if not HAS_PYTHON_HWPX:
            raise ImportError("python-hwpx is required for template analysis")

        if not os.path.exists(hwpx_path):
            raise FileNotFoundError(f"Template file not found: {hwpx_path}")

        result = {
            "filename": os.path.basename(hwpx_path),
            "file_size": os.path.getsize(hwpx_path),
            "text_content": [],
            "placeholders": [],
        }

        try:
            # Use TextExtractor for robust text reading
            with TextExtractor(hwpx_path) as extractor:
                full_text = extractor.extract_text()
            
            result['text_content'] = full_text.splitlines()[:20] # Preview
            
            # Simple regex to find potential placeholders
            import re
            placeholders = set()
            
            # Mustache style {{ key }}
            mustache = re.findall(r'\{\{([^}]+)\}\}', full_text)
            placeholders.update(mustache)
            
            # Bracket style [Key] - heuristic
            brackets = re.findall(r'\[([가-힣a-zA-Z0-9_\s]+)\]', full_text)
            for b in brackets:
                if 1 < len(b) < 30: # Reasonable length
                    placeholders.update([f"[{b}]"])
            
            result['placeholders'] = list(placeholders)
            
        except Exception as e:
            logger.error(f"Error analyzing template: {e}")
            raise e

        return result

    def fill_template(self, template_path: str, output_path: str, data: Dict[str, str]) -> bool:
        """
        Fill template with data using HwpxDocument.replace_text_in_runs.
        """
        if not HAS_PYTHON_HWPX:
            raise ImportError("python-hwpx is required for filling templates")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        try:
            # Open the document
            doc = HwpxDocument.open(template_path)
            
            # Apply replacements
            for key, value in data.items():
                # Direct replacement (e.g. key="[Name]", val="John")
                doc.replace_text_in_runs(key, str(value))
                
                # Mustache fallback (e.g. key="name" -> {{name}})
                if not key.startswith('{{') and not key.startswith('['):
                    doc.replace_text_in_runs(f"{{{{{key}}}}}", str(value))
            
            # Save to output path
            doc.save(output_path)
            return True

        except Exception as e:
            logger.error(f"Failed to fill template: {e}")
            # Clean up if partially created? HwpxDocument.save handles file creation
            raise e
