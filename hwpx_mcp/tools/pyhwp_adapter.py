"""
Pyhwp Adapter - pyhwp based HWP file processing adapter (macOS/Linux support)

This module uses the pyhwp library to directly parse and process HWP files
instead of Windows COM Automation.

Key Features:
- HWP file reading and text extraction
- Document information analysis
- Text searching
- Limited document editing (XML-based)
"""

import os
import re
import tempfile
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger("hwp-mcp-extended.pyhwp_adapter")

try:
    import hwp5

    HAS_PYHWP = True
except ImportError:
    HAS_PYHWP = False
    logger.warning("hwp5 not available. Install with: pip install pyhwp")


# HWPX namespace definitions
HWPX_NAMESPACES = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}


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


@dataclass
class SearchResult:
    """Search result"""

    query: str
    found_count: int
    line_numbers: List[int]
    context_lines: List[str]
    total_matches: int


class PyhwpAdapter:
    """pyhwp-based HWP file processing adapter"""

    def __init__(self):
        """Initialize PyhwpAdapter."""
        self.hwp_file = None
        self.current_path = None
        self.temp_dir = tempfile.mkdtemp()
        self._is_open = False
        self._document_info = None

        if not HAS_PYHWP:
            logger.error(
                "pyhwp is not installed. Please install with: pip install pyhwp"
            )

    def open_document(self, file_path: str) -> bool:
        """Open HWP file.

        Args:
            file_path: HWP file path

        Returns:
            bool: Success status
        """
        if not HAS_PYHWP:
            logger.error("pyhwp not available")
            return False

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        try:
            if self._is_open:
                self.close()

            self.hwp_file = hwp5.HwpFile(file_path)
            self.current_path = os.path.abspath(file_path)
            self._is_open = True

            self._document_info = self._analyze_document()

            logger.info(f"Successfully opened HWP file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to open HWP file {file_path}: {e}")
            return False

    def close(self) -> bool:
        """Close document.

        Returns:
            bool: Success status
        """
        try:
            if self.hwp_file:
                self.hwp_file.close()
            self.hwp_file = None
            self.current_path = None
            self._is_open = False
            self._document_info = None
            return True
        except Exception as e:
            logger.error(f"Failed to close document: {e}")
            return False

    def is_open(self) -> bool:
        """Check if document is open.

        Returns:
            bool: Open status
        """
        return self._is_open and self.hwp_file is not None

    def get_text(self) -> str:
        """Get full document text.

        Returns:
            str: Extracted text
        """
        if not self._is_open:
            logger.warning("No document is open")
            return ""

        try:
            if HAS_PYHWP and self.hwp_file:
                text = self.hwp_file.text()
                if text:
                    return text

            return self._extract_text_via_cli()

        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            return ""

    def _extract_text_via_cli(self) -> str:
        """Extract text using CLI tool (hwp5txt)."""
        try:
            result = subprocess.run(
                ["hwp5txt", self.current_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"hwp5txt failed: {result.stderr}")
                return ""
        except FileNotFoundError:
            logger.warning("hwp5txt not found in PATH")
            return ""
        except subprocess.TimeoutExpired:
            logger.error("hwp5txt timeout")
            return ""
        except Exception as e:
            logger.error(f"CLI text extraction failed: {e}")
            return ""

    def get_info(self) -> Optional[HwpDocumentInfo]:
        """Get document information.

        Returns:
            HwpDocumentInfo: Document information
        """
        if not self._is_open:
            return None

        if self._document_info:
            return self._document_info

        return self._analyze_document()

    def _analyze_document(self) -> HwpDocumentInfo:
        """Analyze document and extract information."""
        text = self.get_text()
        paragraphs = [p for p in text.split("\n") if p.strip()]

        file_size = 0
        if os.path.exists(self.current_path):
            file_size = os.path.getsize(self.current_path)

        tables_count = text.count("表") + text.count("[표") + text.count("표:")

        images_count = 0
        if HAS_PYHWP and self.hwp_file:
            try:
                streams = self.hwp_file.list_streams()
                for stream in streams:
                    if stream.startswith("BinData/BIN"):
                        images_count += 1
            except Exception:
                pass

        pages_count = max(1, len(paragraphs) // 10)

        return HwpDocumentInfo(
            path=self.current_path or "",
            text_length=len(text),
            paragraphs_count=len(paragraphs),
            tables_count=tables_count,
            images_count=images_count,
            pages_count=pages_count,
            file_size=file_size,
        )

    def search_text(
        self, query: str, case_sensitive: bool = True, max_results: int = 50
    ) -> SearchResult:
        """Search text in document.

        Args:
            query: Search query
            case_sensitive: Case sensitive search
            max_results: Maximum number of results

        Returns:
            SearchResult: Search result
        """
        if not self._is_open:
            return SearchResult(query, 0, [], [], 0)

        text = self.get_text()
        lines = text.split("\n")

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.escape(query) if not case_sensitive else query

        line_numbers = []
        context_lines = []
        total_matches = 0

        for i, line in enumerate(lines):
            matches = list(re.finditer(pattern, line, flags))
            if matches:
                line_numbers.append(i)
                context_lines.append(line.strip())
                total_matches += len(matches)

                if len(line_numbers) >= max_results:
                    break

        return SearchResult(
            query=query,
            found_count=len(line_numbers),
            line_numbers=line_numbers,
            context_lines=context_lines,
            total_matches=total_matches,
        )

    def get_paragraphs(self, max_count: int = 100) -> List[Dict[str, Any]]:
        """Get list of paragraphs.

        Args:
            max_count: Maximum number of paragraphs

        Returns:
            List[Dict]: Paragraph information list
        """
        if not self._is_open:
            return []

        text = self.get_text()
        paragraphs = [p for p in text.split("\n") if p.strip()]

        result = []
        for i, paragraph in enumerate(paragraphs[:max_count]):
            result.append(
                {
                    "index": i,
                    "text": paragraph,
                    "length": len(paragraph),
                    "words_count": len(paragraph.split()),
                }
            )

        return result

    def extract_images(self) -> List[Dict[str, Any]]:
        """Extract images from document.

        Returns:
            List[Dict]: Image information list
        """
        if not self._is_open or not HAS_PYHWP:
            return []

        images = []
        try:
            streams = self.hwp_file.list_streams()
            for stream in streams:
                if stream.startswith("BinData/BIN"):
                    images.append({"stream": stream, "type": "image", "size": 0})
        except Exception as e:
            logger.error(f"Failed to extract images: {e}")

        return images

    def to_xml(self, embed_binary: bool = False) -> Optional[str]:
        """Convert HWP file to XML.

        Args:
            embed_binary: Include binary data

        Returns:
            str: XML string
        """
        if not self._is_open or not HAS_PYHWP:
            return None

        try:
            return self.hwp_file.to_xml(embedbin=embed_binary)
        except Exception as e:
            logger.error(f"Failed to convert to XML: {e}")
            return None

    def save_document(self, file_path: str) -> bool:
        """Save document (limited support).

        Args:
            file_path: File path to save

        Returns:
            bool: Success status
        """
        if not self._is_open:
            return False

        try:
            xml_content = self.to_xml()
            if xml_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                return True
        except Exception as e:
            logger.error(f"Failed to save document: {e}")

        return False

    def replace_text(self, find_text: str, replace_text: str) -> int:
        """Replace text (limited support).

        Args:
            find_text: Text to find
            replace_text: Text to replace

        Returns:
            int: Number of replacements
        """
        logger.warning("Text replacement not yet implemented in pyhwp adapter")
        return 0

    def create_document_from_template(
        self, template: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create document from template (text-based output only).

        Note: pyhwp only supports reading HWP files, not creating them.
        This method generates text-based output and saves as .txt or .md file.

        Args:
            template: Template dictionary with template_content
            data: Data to fill in template

        Returns:
            dict: Creation result with status and info
        """
        try:
            # Fill template content
            filled_content = template.get("template_content", "")
            for field_name, value in data.items():
                if value is not None:
                    placeholder = f"{{{{{{{field_name}}}}}}}"
                    filled_content = filled_content.replace(placeholder, str(value))

            # output paths
            output_paths = []

            # Save as .txt
            txt_path = os.path.join(self.temp_dir, f"template_{template['id']}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(filled_content)
            output_paths.append(txt_path)

            # Save as .md (markdown)
            md_path = os.path.join(self.temp_dir, f"template_{template['id']}.md")
            md_content = f"# {template['name']}\n\n{filled_content}"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            output_paths.append(md_path)

            return {
                "status": "success",
                "template_id": template["id"],
                "template_name": template["name"],
                "filled_content": filled_content,
                "output_paths": output_paths,
                "note": "HWP file creation not supported on this platform. Text/Markdown files generated.",
            }

        except Exception as e:
            logger.error(f"Failed to create document from template: {e}")
            return {"status": "error", "error": str(e)}

    def create_new_document(self) -> bool:
        """Clean up temporary files."""
        try:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        self.cleanup()


# Global adapter instance
_pyhwp_adapter: Optional[PyhwpAdapter] = None


def get_pyhwp_adapter() -> Optional[PyhwpAdapter]:
    """Get global PyhwpAdapter instance.

    Returns:
        PyhwpAdapter: Adapter instance
    """
    global _pyhwp_adapter
    if _pyhwp_adapter is None:
        _pyhwp_adapter = PyhwpAdapter()
    return _pyhwp_adapter


def reset_pyhwp_adapter() -> None:
    """Reset global PyhwpAdapter instance."""
    global _pyhwp_adapter
    if _pyhwp_adapter:
        _pyhwp_adapter.close()
        _pyhwp_adapter.cleanup()
    _pyhwp_adapter = None


def is_hwp_file(file_path: str) -> bool:
    """Check if file is HWP format.

    Args:
        file_path: File path

    Returns:
        bool: HWP file status
    """
    if not os.path.exists(file_path):
        return False

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in [".hwp", ".hwpx"]:
        return False

    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            return header in [b"HWP5", b"HWPX"]
    except Exception:
        return False


def extract_text_from_hwp(file_path: str) -> str:
    """Extract text from HWP file (convenience function).

    Args:
        file_path: HWP file path

    Returns:
        str: Extracted text
    """
    with PyhwpAdapter() as adapter:
        if adapter.open_document(file_path):
            return adapter.get_text()
    return ""


def extract_text_from_hwpx(file_path: str) -> str:
    """Extract text from HWPX file (native cross-platform format).

    HWPX is a ZIP archive containing XML files. This function extracts
    text from the section0.xml file which contains the document content.

    Args:
        file_path: HWPX file path

    Returns:
        str: Extracted text
    """
    if not os.path.exists(file_path):
        logger.error(f"HWPX file not found: {file_path}")
        return ""

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Read section0.xml which contains the document content
            section_xml = zf.read("Contents/section0.xml")
            return _parse_hwpx_section_text(section_xml)
    except zipfile.BadZipFile:
        logger.error(f"Invalid HWPX file (not a ZIP): {file_path}")
        return ""
    except KeyError as e:
        logger.error(f"HWPX file missing expected content: {e}")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract text from HWPX: {e}")
        return ""


def _parse_hwpx_section_text(xml_content: bytes) -> str:
    """Parse HWPX section0.xml and extract text content.

    Args:
        xml_content: Raw XML bytes from section0.xml

    Returns:
        str: Extracted text
    """
    try:
        root = ET.fromstring(xml_content)

        text_parts = []

        # Find all paragraph elements (hp:p)
        for para in root.findall(".//hp:p", HWPX_NAMESPACES):
            para_text = _extract_text_from_element(para)
            if para_text:
                text_parts.append(para_text)

        return "\n".join(text_parts)
    except ET.ParseError as e:
        logger.error(f"Failed to parse HWPX XML: {e}")
        return ""


def _extract_text_from_element(element: ET.Element) -> str:
    """Recursively extract text from an XML element.

    Args:
        element: XML element

    Returns:
        str: Extracted text content
    """
    text_parts = []

    # Get text before first child
    if element.text:
        text_parts.append(element.text)

    # Get text from children
    for child in element:
        child_text = _extract_text_from_element(child)
        if child_text:
            text_parts.append(child_text)

        # Get tail text (text after child element)
        if child.tail:
            text_parts.append(child.tail)

    return "".join(text_parts)


def get_hwpx_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get information about an HWPX file.

    Args:
        file_path: HWPX file path

    Returns:
        dict: File information or None if failed
    """
    if not os.path.exists(file_path):
        return None

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            info = {
                "path": file_path,
                "file_size": os.path.getsize(file_path),
                "file_type": "HWPX (OWPML)",
            }

            # Get list of files in archive
            info["archive_files"] = zf.namelist()

            # Try to read header.xml for document properties
            try:
                header_xml = zf.read("Contents/header.xml")
                header_info = _parse_hwpx_header(header_xml)
                info.update(header_info)
            except Exception:
                pass

            # Count paragraphs
            try:
                section_xml = zf.read("Contents/section0.xml")
                para_count = _count_hwpx_paragraphs(section_xml)
                info["paragraphs_count"] = para_count
            except Exception:
                info["paragraphs_count"] = 0

            return info
    except Exception as e:
        logger.error(f"Failed to get HWPX info: {e}")
        return None


def _parse_hwpx_header(xml_content: bytes) -> Dict[str, Any]:
    """Parse HWPX header.xml for document properties.

    Args:
        xml_content: Raw XML bytes from header.xml

    Returns:
        dict: Parsed header information
    """
    try:
        root = ET.fromstring(xml_content)

        info = {}

        # Parse font faces
        font_faces = []
        for font in root.findall(".//hh:fontFace", HWPX_NAMESPACES):
            font_info = {
                "lang": font.get("lang", ""),
                "fontName": font.get("fontName", ""),
            }
            font_faces.append(font_info)
        info["font_faces"] = font_faces

        # Parse styles
        styles = []
        for style in root.findall(".//hh:style", HWPX_NAMESPACES):
            style_info = {
                "id": style.get("id", ""),
                "type": style.get("type", ""),
                "name": style.get("name", ""),
            }
            styles.append(style_info)
        info["styles"] = styles

        return info
    except Exception as e:
        logger.error(f"Failed to parse HWPX header: {e}")
        return {}


def _count_hwpx_paragraphs(xml_content: bytes) -> int:
    """Count paragraphs in HWPX section0.xml.

    Args:
        xml_content: Raw XML bytes from section0.xml

    Returns:
        int: Paragraph count
    """
    try:
        root = ET.fromstring(xml_content)
        paras = root.findall(".//hp:p", HWPX_NAMESPACES)
        return len(paras)
    except Exception:
        return 0
