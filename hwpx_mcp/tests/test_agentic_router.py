from hwpx_mcp.agentic.models import ToolRecord
from hwpx_mcp.agentic.router import HierarchicalRouter


def _records() -> list[ToolRecord]:
    return [
        ToolRecord(
            tool_id="hwp_export_pdf:1",
            name="hwp_export_pdf",
            description="Export document to PDF",
            input_schema={},
            output_schema=None,
            group="export_convert",
            tags=("export",),
            schema_hash="1",
        ),
        ToolRecord(
            tool_id="hwp_insert_text:2",
            name="hwp_insert_text",
            description="Insert text into current document",
            input_schema={},
            output_schema=None,
            group="text_insertion",
            tags=("generic",),
            schema_hash="2",
        ),
    ]


def test_router_selects_expected_group():
    router = HierarchicalRouter(_records())
    route = router.route_group("please export this report to pdf")
    assert route.group == "export_convert"
    assert route.confidence > 0


def test_router_selects_in_group_tools():
    router = HierarchicalRouter(_records())
    scores = router.select_tools(query="insert body text", group="text_insertion", top_k=1)
    assert len(scores) == 1
    assert scores[0].tool_id == "hwp_insert_text:2"
