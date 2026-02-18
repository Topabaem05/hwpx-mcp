from hwpx_mcp.agentic.models import ToolRecord
from hwpx_mcp.agentic.retrieval import HybridRetriever


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


def test_hybrid_retriever_finds_export_tool():
    retriever = HybridRetriever(_records())
    results = retriever.search(query="export as pdf", top_k=2)
    assert results
    assert results[0].tool_id == "hwp_export_pdf:1"


def test_hybrid_retriever_group_filter():
    retriever = HybridRetriever(_records())
    results = retriever.search(query="insert text", groups=["text_insertion"], top_k=2)
    assert len(results) == 1
    assert results[0].tool_id == "hwp_insert_text:2"
