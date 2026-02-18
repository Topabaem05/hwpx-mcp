from __future__ import annotations

from .models import GroupName

GROUP_KEYWORDS: dict[GroupName, tuple[str, ...]] = {
    "document_lifecycle": (
        "connect",
        "disconnect",
        "create",
        "open",
        "save",
        "close",
        "document",
    ),
    "text_insertion": (
        "insert_text",
        "font",
        "charshape",
        "parashape",
        "paragraph",
        "heading",
        "bold",
        "italic",
        "underline",
    ),
    "table_chart": (
        "table",
        "cell",
        "chart",
        "picture",
        "image",
        "equation",
    ),
    "field_meta": (
        "field",
        "bookmark",
        "metatag",
        "metadata",
        "template",
    ),
    "find_replace": (
        "find",
        "replace",
        "search",
    ),
    "xml_direct": (
        "xml",
        "xpath",
        "validate",
        "parse_section",
        "smart_patch",
    ),
    "export_convert": (
        "export",
        "convert",
        "pdf",
        "html",
    ),
    "util_debug": (
        "ping",
        "capabilities",
        "platform_info",
        "get_document_info",
        "page_count",
    ),
    "other": (),
}


def classify_group(tool_name: str, description: str) -> GroupName:
    lowered = f"{tool_name} {description}".lower()
    for group, keywords in GROUP_KEYWORDS.items():
        if group == "other":
            continue
        if any(keyword in lowered for keyword in keywords):
            return group
    return "other"
