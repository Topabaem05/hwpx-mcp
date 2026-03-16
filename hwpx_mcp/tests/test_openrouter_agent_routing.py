from hwpx_mcp.agentic.openrouter_agent import _detect_case
from hwpx_mcp.agentic.openrouter_agent import _parse_intent
from hwpx_mcp.agentic.openrouter_agent import _route_subagent
from hwpx_mcp.agentic.openrouter_agent import _subagent_tool_allowlist


def test_parse_intent_treats_form_edit_as_table_not_template() -> None:
    assert _parse_intent("공식문서 양식 표를 수정해줘") == "table"


def test_parse_intent_treats_form_field_request_as_field_form() -> None:
    assert _parse_intent("신청서 양식 필드를 채워줘") == "field_form"


def test_parse_intent_treats_template_list_as_template() -> None:
    assert _parse_intent("템플릿 목록 보여줘") == "template"


def test_parse_intent_detects_existing_document_edit_as_open_document() -> None:
    assert _parse_intent('기존 문서 "official.hwpx" 열어서 수정해줘') == "open_document"


def test_parse_intent_detects_path_based_edit_without_open_keyword_as_open_document() -> (
    None
):
    assert _parse_intent('"official.hwpx"에 "승인 완료" 추가해줘') == "open_document"


def test_parse_intent_keeps_literal_form_search_as_search() -> None:
    assert _parse_intent('"양식" 검색해줘') == "search"


def test_detect_case_does_not_force_form_table_request_into_template_workflow() -> None:
    tool_names = {"hwp_list_templates", "hwp_create_table", "hwp_insert_text"}

    assert (
        _detect_case("공식문서 양식 표를 수정해줘", tool_names) != "template_workflow"
    )


def test_route_subagent_keeps_table_and_field_requests_in_document_agent() -> None:
    assert _route_subagent("table", "windows_com_full") == "document_agent"
    assert _route_subagent("field_form", "windows_com_full") == "document_agent"


def test_document_agent_allowlist_includes_open_table_and_field_tools() -> None:
    open_allowlist = _subagent_tool_allowlist("document_agent", "open_document")
    table_allowlist = _subagent_tool_allowlist("document_agent", "table")
    field_allowlist = _subagent_tool_allowlist("document_agent", "field_form")

    assert "hwp_platform_info" in open_allowlist
    assert "hwp_open" in open_allowlist
    assert "hwp_create_table" in table_allowlist
    assert "hwp_create_field" in field_allowlist
    assert "hwp_put_field_text" in field_allowlist


def test_open_document_allowlist_excludes_create_tools() -> None:
    allowlist = _subagent_tool_allowlist("document_agent", "open_document")

    assert "hwp_create" not in allowlist
    assert "hwp_create_hwpx" not in allowlist


def test_template_agent_allowlist_can_create_from_template() -> None:
    allowlist = _subagent_tool_allowlist("template_agent", "template")

    assert allowlist == [
        "hwp_list_templates",
        "hwp_search_template",
        "hwp_create_from_template",
    ]
