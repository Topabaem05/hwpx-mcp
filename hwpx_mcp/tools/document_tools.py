"""
Document Tools for HWP MCP Server
Unified document reading and searching tools for HWP (binary) and HWPX (XML)
"""

import os
import logging
from typing import Optional, Dict, Any, Callable

from pydantic import BaseModel, Field

# HWP (Binary) Adapter & Fallback HWPX tools
from hwpx_mcp.tools.pyhwp_adapter import extract_text_from_hwpx, get_hwpx_info

# HWPX (XML) Library (Preferred)
try:
    from hwpx.tools.text_extractor import TextExtractor
    from hwpx.document import HwpxDocument

    HAS_PYTHON_HWPX = True
except ImportError:
    HAS_PYTHON_HWPX = False

logger = logging.getLogger("hwp-mcp-extended.documents")


class DocumentInfo(BaseModel):
    """Document information schema"""

    path: Optional[str] = Field(default=None, description="Document path")
    text_length: int = Field(default=0, description="Text length")
    paragraphs_count: int = Field(default=0, description="Paragraph count")
    tables_count: int = Field(default=0, description="Table count")


def register_document_tools(mcp, get_pyhwp_adapter: Callable) -> None:
    """Register document tools with MCP server."""

    @mcp.tool()
    def hwp_read_document(path: Optional[str] = None) -> Dict[str, Any]:
        """
        Read document content from .hwp or .hwpx files.
         Automatically detects format and uses appropriate extractor.

        Args:
            path: Document path (None for current document)

        Returns:
            dict: Document content and information
                - status: Operation status
                - text: Extracted text
                - info: Document information
                - preview: Text preview (first 1000 chars)

        Example:
            hwp_read_document(path="documents/report.hwp")
            hwp_read_document(path="documents/report.hwpx")
        """
        try:
            if path and not os.path.exists(path):
                return {"status": "error", "error": f"File not found: {path}"}

            ext = os.path.splitext(path)[1].lower() if path else ""

            # --- HWPX Handling ---
            if ext == ".hwpx":
                # Priority 1: python-hwpx (Full features)
                if HAS_PYTHON_HWPX:
                    try:
                        with TextExtractor(path) as extractor:
                            text = extractor.extract_text()

                        doc = HwpxDocument.open(path)
                        paragraphs_count = len(doc.paragraphs)

                        return {
                            "status": "success",
                            "text": text,
                            "info": {
                                "path": path,
                                "file_type": "HWPX",
                                "file_size": os.path.getsize(path),
                                "paragraphs_count": paragraphs_count,
                                "text_length": len(text),
                            },
                            "preview": text[:1000]
                            + ("..." if len(text) > 1000 else ""),
                        }
                    except Exception as e:
                        logger.warning(
                            f"python-hwpx failed, falling back to manual parsing: {e}"
                        )

                # Priority 2: Manual XML parsing (Fallback)
                try:
                    text = extract_text_from_hwpx(path)
                    info = get_hwpx_info(path) or {}

                    return {
                        "status": "success",
                        "text": text,
                        "info": {
                            "path": path,
                            "file_type": "HWPX (Fallback)",
                            "file_size": info.get("file_size", 0),
                            "paragraphs_count": info.get("paragraphs_count", 0),
                            "text_length": len(text),
                        },
                        "preview": text[:1000] + ("..." if len(text) > 1000 else ""),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to read HWPX: {str(e)}",
                    }

            # --- HWP Handling (pyhwp) ---
            adapter = get_pyhwp_adapter()
            if not adapter:
                return {"status": "error", "error": "PyhwpAdapter not available"}

            if path:
                if not adapter.open_document(path):
                    return {"status": "error", "error": "Failed to open document"}

            text = adapter.get_text()
            info = adapter.get_info()

            if not info:
                return {"status": "error", "error": "Failed to get document info"}

            return {
                "status": "success",
                "text": text,
                "info": {
                    "path": info.path,
                    "text_length": info.text_length,
                    "paragraphs_count": info.paragraphs_count,
                    "tables_count": info.tables_count,
                    "images_count": info.images_count,
                    "pages_count": info.pages_count,
                    "file_size": info.file_size,
                },
                "preview": text[:1000] + ("..." if len(text) > 1000 else ""),
            }

        except Exception as e:
            logger.error(f"Error reading document: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_search_text(
        query: str,
        path: Optional[str] = None,
        case_sensitive: bool = True,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        """
        Search text in document.

        Args:
            query: Text to search
            path: Document path (optional)
            case_sensitive: Case sensitive search
            max_results: Maximum number of results

        Returns:
            dict: Search results
        """
        try:
            if path and not os.path.exists(path):
                return {"status": "error", "error": f"File not found: {path}"}

            ext = os.path.splitext(path)[1].lower() if path else ""

            # --- HWPX Handling ---
            if ext == ".hwpx":
                # Use unified reading to get text first
                read_result = hwp_read_document(path)
                if read_result.get("status") != "success":
                    return {"status": "error", "error": read_result.get("error")}

                text = read_result.get("text", "")
                lines = text.splitlines()
                found_count = 0
                matches = []

                for i, line in enumerate(lines):
                    if found_count >= max_results:
                        break

                    line_to_check = line if case_sensitive else line.lower()
                    query_to_check = query if case_sensitive else query.lower()

                    if query_to_check in line_to_check:
                        found_count += 1
                        matches.append({"line": i + 1, "text": line.strip()})

                return {
                    "status": "success" if found_count > 0 else "not_found",
                    "query": query,
                    "found_count": found_count,
                    "matches": matches,
                    "file_type": "HWPX",
                }

            # --- HWP Handling ---
            adapter = get_pyhwp_adapter()
            if not adapter:
                return {"status": "error", "error": "PyhwpAdapter not available"}

            if path:
                if not adapter.open_document(path):
                    return {"status": "error", "error": f"Cannot open document: {path}"}

            search_result = adapter.search_text(query, case_sensitive, max_results)

            return {
                "status": "success" if search_result.found_count > 0 else "not_found",
                "query": query,
                "found_count": search_result.found_count,
                "total_matches": search_result.total_matches,
                "line_numbers": search_result.line_numbers,
                "context_lines": search_result.context_lines,
            }

        except Exception as e:
            logger.error(f"Error searching text: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_get_document_info(path: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed document information."""
        return hwp_read_document(path)  # Reuse unified reader

    @mcp.tool()
    def hwp_get_paragraphs(
        path: Optional[str] = None, max_count: int = 100
    ) -> Dict[str, Any]:
        """Get list of paragraphs from document."""
        try:
            if path and not os.path.exists(path):
                return {"status": "error", "error": f"File not found: {path}"}

            ext = os.path.splitext(path)[1].lower() if path else ""

            if ext == ".hwpx" and HAS_PYTHON_HWPX:
                doc = HwpxDocument.open(path)
                paragraphs = [p.text for p in doc.paragraphs[:max_count]]
                return {
                    "status": "success",
                    "paragraphs": paragraphs,
                    "total_count": len(paragraphs),
                    "file_type": "HWPX",
                }

            adapter = get_pyhwp_adapter()
            if not adapter:
                return {"status": "error", "error": "PyhwpAdapter not available"}

            if path:
                if not adapter.open_document(path):
                    return {"status": "error", "error": f"Cannot open document: {path}"}

            paragraphs = adapter.get_paragraphs(max_count)

            return {
                "status": "success",
                "paragraphs": paragraphs,
                "total_count": len(paragraphs),
            }

        except Exception as e:
            logger.error(f"Error getting paragraphs: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_extract_images(path: Optional[str] = None) -> Dict[str, Any]:
        """Extract images from document (HWP/HWPX)."""
        try:
            if path and not os.path.exists(path):
                return {"status": "error", "error": f"File not found: {path}"}

            ext = os.path.splitext(path)[1].lower() if path else ""

            if ext == ".hwpx":
                # HWPX image extraction (manual zip scan)
                import zipfile

                images = []
                try:
                    with zipfile.ZipFile(path, "r") as zf:
                        for name in zf.namelist():
                            if name.startswith("BinData/") and any(
                                name.lower().endswith(ext)
                                for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
                            ):
                                images.append(
                                    {
                                        "name": name,
                                        "size": zf.getinfo(name).file_size,
                                        "type": "image",
                                    }
                                )
                    return {"status": "success", "images": images, "count": len(images)}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

            adapter = get_pyhwp_adapter()
            if not adapter:
                return {"status": "error", "error": "PyhwpAdapter not available"}

            if path:
                if not adapter.open_document(path):
                    return {"status": "error", "error": f"Cannot open document: {path}"}

            images = adapter.extract_images()

            return {"status": "success", "images": images, "count": len(images)}

        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_to_xml(
        path: Optional[str] = None, embed_binary: bool = False
    ) -> Dict[str, Any]:
        """Convert HWP file to XML."""
        try:
            adapter = get_pyhwp_adapter()
            if not adapter:
                return {"status": "error", "error": "PyhwpAdapter not available"}

            if path:
                if not adapter.open_document(path):
                    return {"status": "error", "error": f"Cannot open document: {path}"}

            xml_content = adapter.to_xml(embed_binary)

            if xml_content is None:
                return {"status": "error", "error": "Failed to convert to XML"}

            return {
                "status": "success",
                "xml": xml_content,
                "length": len(xml_content),
                "embed_binary": embed_binary,
            }

        except Exception as e:
            logger.error(f"Error converting to XML: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_read_hwpx(path: str) -> Dict[str, Any]:
        """
        Deprecated: Use hwp_read_document instead.
        Read HWPX (native cross-platform) document.
        """
        return hwp_read_document(path)
