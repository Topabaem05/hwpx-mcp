# HWPX-MCP

**[English](README.md) | [한국어](README.kr.md)**

한글(HWP/HWPX) 문서를 생성하고 편집하기 위한 Model Context Protocol (MCP) 서버입니다. 이 서버는 AI 어시스턴트(Claude, Cursor 등)가 한글 문서를 프로그래밍 방식으로 생성, 편집 및 조작할 수 있도록 지원합니다.

## 주요 기능

- **크로스 플랫폼 지원**: Windows (COM Automation) 및 macOS/Linux (python-hwpx)에서 동작
- **120+ MCP 도구**: 문서 조작을 위한 포괄적인 도구 세트
- **템플릿 지원**: 필드 대체가 가능한 템플릿에서 문서 생성
- **차트 생성**: 문서에 차트 삽입 및 구성
- **수식 지원**: 수학 공식 (LaTeX/Script) 삽입
- **표 조작**: 표 생성, 편집, 서식 지정의 전체 기능
- **서식 제어**: 문자 및 문단 서식 지정

## 빠른 시작 (복사 & 붙여넣기)

### 1. 설치

<details>
<summary><b>uv 사용 (권장)</b></summary>

```bash
git clone https://github.com/Topabaem05/hwpx-mcp.git
cd hwpx-mcp && uv pip install -e .
```

</details>

<details>
<summary><b>Anaconda/Conda 사용</b></summary>

```bash
git clone https://github.com/Topabaem05/hwpx-mcp.git
cd hwpx-mcp
conda create -n hwpx-mcp python=3.11 -y
conda activate hwpx-mcp
pip install -e .
```

</details>

### 2. 설치 경로 확인

`hwpx-mcp` 디렉토리에서 아래 명령어를 실행하여 경로를 복사하세요:

```bash
# macOS/Linux
pwd | pbcopy  # macOS (클립보드에 복사)
pwd           # Linux (수동으로 복사)

# Windows (PowerShell)
(Get-Location).Path | clip
```

**Anaconda 사용자**는 Python 경로도 확인하세요:

```bash
# macOS/Linux
which python | pbcopy  # conda activate hwpx-mcp 실행 후

# Windows (PowerShell)
(Get-Command python).Source | clip
```

### 3. MCP 클라이언트 설정

2단계에서 얻은 경로를 아래 설정에 붙여넣으세요:

<details>
<summary><b>Claude Desktop (macOS) - uv</b></summary>

`~/Library/Application Support/Claude/claude_desktop_config.json` 편집:

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

`~/Library/Application Support/Claude/claude_desktop_config.json` 편집:

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

> 예시 경로:
> - Python: `/Users/username/anaconda3/envs/hwpx-mcp/bin/python`
> - cwd: `/Users/username/projects/hwpx-mcp`

</details>

<details>
<summary><b>Claude Desktop (Windows) - uv</b></summary>

`%APPDATA%\Claude\claude_desktop_config.json` 편집:

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

`%APPDATA%\Claude\claude_desktop_config.json` 편집:

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

> 예시 경로:
> - Python: `C:\Users\username\anaconda3\envs\hwpx-mcp\python.exe`
> - cwd: `C:\Users\username\projects\hwpx-mcp`

</details>

<details>
<summary><b>Claude Desktop (Linux) - uv</b></summary>

`~/.config/Claude/claude_desktop_config.json` 편집:

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

`~/.config/Claude/claude_desktop_config.json` 편집:

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

> 예시 경로:
> - Python: `/home/username/anaconda3/envs/hwpx-mcp/bin/python`
> - cwd: `/home/username/projects/hwpx-mcp`

</details>

<details>
<summary><b>Cursor - uv</b></summary>

`~/.cursor/mcp.json` (macOS/Linux) 또는 `%USERPROFILE%\.cursor\mcp.json` (Windows) 편집:

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

`~/.cursor/mcp.json` (macOS/Linux) 또는 `%USERPROFILE%\.cursor\mcp.json` (Windows) 편집:

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

VS Code `settings.json`에 추가:

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

VS Code `settings.json`에 추가:

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

프로젝트 루트에 `opencode.json` 생성 또는 편집 (전역 설정: `~/.config/opencode/opencode.json`):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "hwpx-mcp": {
      "type": "local",
      "command": ["uv", "--directory", "/여기에/경로/붙여넣기", "run", "hwpx-mcp"],
      "enabled": true
    }
  }
}
```

</details>

<details>
<summary><b>OpenCode - Anaconda</b></summary>

프로젝트 루트에 `opencode.json` 생성 또는 편집 (전역 설정: `~/.config/opencode/opencode.json`):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "hwpx-mcp": {
      "type": "local",
      "command": ["/여기에/콘다/파이썬/경로/붙여넣기", "-m", "hwpx_mcp.server"],
      "enabled": true,
      "environment": {
        "PYTHONPATH": "/여기에/HWPX-MCP/경로/붙여넣기"
      }
    }
  }
}
```

> 예시 경로:
> - Python: `/Users/username/anaconda3/envs/hwpx-mcp/bin/python` (macOS/Linux)
> - Python: `C:\\Users\\username\\anaconda3\\envs\\hwpx-mcp\\python.exe` (Windows)
> - PYTHONPATH: `/Users/username/projects/hwpx-mcp`

</details>

### 4. MCP 클라이언트를 재시작하고 HWP 도구를 사용하세요!

## 도구 참고서 (Tool Reference)

### 1. 문서 관리 (Document Management)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_connect` | HWP 컨트롤러 연결 (Windows COM 또는 크로스 플랫폼 자동 선택) | 전체 |
| `hwp_create` | 새 HWP 문서 생성 | 전체 |
| `hwp_open` | 기존 HWP/HWPX 문서 열기 | 전체 |
| `hwp_save` | 현재 문서 저장 | 전체 |
| `hwp_save_as` | 문서를 지정된 형식(hwp, hwpx, pdf)으로 저장 | 전체 |
| `hwp_close` | 현재 문서 닫기 | 전체 |
| `hwp_disconnect` | HWP 컨트롤러 연결 해제 및 리소스 해제 | 전체 |
| `hwp_set_edit_mode` | 문서 모드 설정 (편집, 읽기 전용, 양식) | Windows |

### 2. 텍스트 및 서식 (Text & Formatting)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_insert_text` | 현재 커서 위치에 텍스트 삽입 | 전체 |
| `hwp_get_text` | 현재 문서의 모든 텍스트 가져오기 | 전체 |
| `hwp_set_font` | 글꼴 이름 및 크기 설정 | 전체 |
| `hwp_set_charshape` | 글자 모양 설정 (진하게, 기울임, 밑줄, 색상) | Windows |
| `hwp_get_charshape` | 현재 글자 모양 정보 가져오기 | Windows |
| `hwp_set_parashape` | 문단 모양 설정 (정렬, 줄 간격) | Windows |
| `hwp_toggle_bold` | 진하게 서식 토글 | Windows |
| `hwp_toggle_italic` | 기울임 서식 토글 | Windows |
| `hwp_toggle_underline` | 밑줄 서식 토글 | Windows |
| `hwp_toggle_strikethrough` | 취소선 서식 토글 | Windows |
| `hwp_insert_dutmal` | 덧말 넣기 (본말, 덧말, 위치) | Windows |

### 3. 표 작업 (Tables)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_table` | 지정된 행과 열로 표 생성 | 전체 |
| `hwp_set_cell_text` | 특정 셀(행, 열)에 텍스트 설정 | 전체 |
| `hwp_get_cell_text` | 특정 셀의 텍스트 가져오기 | 전체 |
| `hwp_table_format_cell` | 표 셀 서식 지정 (테두리 종류/두께, 채우기 색상) | Windows |
| `hwp_table_split_cell` | 현재 셀을 행/열로 나누기 | Windows |
| `hwp_table_merge_cells` | 선택한 셀 합치기 | Windows |
| `hwp_goto_cell` | 특정 셀 주소(예: 'A1')로 이동 | Windows |
| `hwp_get_cell_addr` | 현재 셀 주소 가져오기 (예: 'A1') | Windows |
| `hwp_adjust_cellwidth` | 열 너비 조정 (비율 모드 지원) | Windows |

### 4. 페이지 및 레이아웃 (Page & Layout)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_page_setup` | 페이지 레이아웃 설정 (여백, 방향, 용지 크기) | Windows |
| `hwp_setup_columns` | 다단 설정 (단 개수, 너비 동일, 간격) | Windows |
| `hwp_insert_page_number` | 위치 및 형식 옵션으로 쪽 번호 삽입 | Windows |
| `hwp_insert_header_footer` | 텍스트 내용으로 머리말 또는 꼬리말 삽입 | Windows |
| `hwp_set_page_hiding` | 현재 쪽 감추기 (머리말, 꼬리말, 쪽 번호 등) | Windows |
| `hwp_break_page` | 쪽 나누기 삽입 | Windows |
| `hwp_break_section` | 구역 나누기 삽입 | Windows |
| `hwp_get_page_count` | 전체 페이지 수 가져오기 | 전체 |
| `hwp_goto_page` | 특정 페이지(0부터 시작)로 이동 | 전체 |

### 5. 탐색 및 선택 (Navigation & Selection)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_move_to` | 정밀 커서 이동 (37개 이상 타겟: 문서 시작, 문단, 셀 등) | Windows |
| `hwp_select_range` | 문단 및 위치 인덱스로 텍스트 범위 선택 | Windows |
| `hwp_insert_bookmark` | 커서 위치에 책갈피 삽입 | Windows |
| `hwp_move_to_start` | 문서 시작으로 커서 이동 | Windows |
| `hwp_move_to_end` | 문서 끝으로 커서 이동 | Windows |
| `hwp_find` | 문서에서 텍스트 찾기 | 전체 |
| `hwp_find_replace` | 텍스트 찾기 및 바꾸기 (1회) | Windows |
| `hwp_find_replace_all` | 텍스트 모두 찾기 및 바꾸기 | Windows |
| `hwp_find_advanced` | 정규식 지원 고급 찾기 | Windows |

### 6. 개체 및 삽입 (Objects & Inserts)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_insert_picture` | 현재 커서 위치에 이미지 삽입 | 전체 |
| `hwp_insert_background` | 배경 이미지 삽입 (바둑판식, 가운데, 늘이기) | Windows |
| `hwp_insert_hyperlink` | 커서 위치에 하이퍼링크 삽입 | Windows |
| `hwp_insert_note` | 각주 또는 미주 삽입 | Windows |
| `hwp_insert_index_mark` | 찾아보기 표시 넣기 | Windows |
| `hwp_insert_auto_number` | 자동 번호 넣기 (쪽, 그림, 표 등) | Windows |
| `hwp_create_chart` | 데이터로 차트 생성 | 전체 |
| `hwp_create_equation` | 수학 수식 생성 | 전체 |

### 7. 필드 및 메타데이터 (Fields & Metadata)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_field` | 새 필드(누름틀) 생성 | Windows |
| `hwp_put_field_text` | 이름으로 필드에 텍스트 설정 | Windows |
| `hwp_get_field_text` | 필드에서 텍스트 가져오기 | Windows |
| `hwp_get_field_list` | 모든 필드 이름 목록 가져오기 | Windows |
| `hwp_field_exists` | 필드 존재 여부 확인 | Windows |
| `hwp_manage_metatags` | 문서 메타태그 관리 (숨겨진 메타데이터) | Windows |

### 8. 템플릿 (Templates)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_list_templates` | 사용 가능한 모든 HWPX 템플릿 나열 | 전체 |
| `hwp_create_from_template` | 템플릿 파일에서 문서 생성 | 전체 |
| `hwp_fill_template` | 데이터로 템플릿 필드 채우기 | 전체 |
| `hwp_recommend_template` | 사용자 요구사항에 기반한 템플릿 추천 | 전체 |
| `hwp_use_template` | 템플릿 복제 및 편집을 위해 열기 | 전체 |
| `hwp_get_template_info` | 특정 템플릿에 대한 상세 정보 가져오기 | 전체 |

### 9. 고급 및 유틸리티 (Advanced & Utility)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_run_action` | 800개 이상의 HWP 액션 ID 실행 | Windows |
| `hwp_platform_info` | 현재 플랫폼 정보 가져오기 | 전체 |
| `hwp_capabilities` | 전체 기능 지원표 가져오기 | 전체 |
| `hwp_convert_unit` | HwpUnit과 밀리미터 간 변환 | 전체 |
| `hwp_get_head_types` | 사용 가능한 제목 유형 가져오기 | 전체 |
| `hwp_get_line_types` | 사용 가능한 선 유형 가져오기 | 전체 |
| `hwp_get_line_widths` | 사용 가능한 선 두께 가져오기 | 전체 |
| `hwp_get_number_formats` | 사용 가능한 숫자 형식 가져오기 | 전체 |

### 10. XML 처리 및 보안 (XML Processing & Security)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_xml_validate_content` | HWPX XML 문법/스키마 검증 | 전체 |
| `hwp_xml_xpath_query` | HWPX XML에 대해 XPath 쿼리 실행 | 전체 |
| `hwp_xml_parse_section` | 섹션 XML을 구조화된 JSON으로 파싱 | 전체 |
| `hwp_smart_patch_xml` | 스마트 필터링으로 HWPX XML 검증 및 패치 | 전체 |

### 11. 변환 및 내보내기 (Conversion & Export)
| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_convert_format` | HWP, HWPX, PDF, HTML 간 포맷 변환 | Windows |
| `hwp_export_pdf` | PDF로 내보내기 | Windows |
| `hwp_export_html` | HTML로 내보내기 | Windows |

## 사용 예시

### 기본 문서 생성

```python
# HWP에 연결
hwp_connect(visible=True)

# 새 문서 생성
hwp_create()

# 글꼴 설정 및 텍스트 삽입
hwp_set_font(font_name="NanumGothic", size=12)
hwp_insert_text("Hello, HWP MCP!")

# 문서 저장
hwp_save_as(path="output.hwpx", format="hwpx")
hwp_disconnect()
```

### 표 생성

```python
hwp_connect()
hwp_create()

# 3x2 표 생성
hwp_create_table(rows=3, cols=2)

# 헤더 행 채우기
hwp_set_cell_text(row=0, col=0, text="이름")
hwp_set_cell_text(row=0, col=1, text="값")

# 데이터 채우기
hwp_set_cell_text(row=1, col=0, text="항목 1")
hwp_set_cell_text(row=1, col=1, text="100")
hwp_set_cell_text(row=2, col=0, text="항목 2")
hwp_set_cell_text(row=2, col=1, text="200")

# 저장
hwp_save_as(path="table_example.hwpx")
```

### 템플릿 사용

```python
hwp_connect()
hwp_open(path="template.hwpx")

# 필드 채우기
hwp_put_field_text(name="title", text="내 문서 제목")
hwp_put_field_text(name="author", text="홍길동")
hwp_put_field_text(name="date", text="2024-01-15")

# 새 문서로 저장
hwp_save_as(path="filled_document.hwpx")
```

### 텍스트 검색 및 바꾸기

```python
hwp_connect()
hwp_open(path="document.hwpx")

# 텍스트 찾기
result = hwp_find(text="古いテキスト")
if result["found"]:
    print("텍스트를 찾았습니다!")

# 모든 occurrence 바꾸기
result = hwp_find_replace_all(find_text="古い", replace_text="新しい")
print(f"{result['count']}개 교체됨")

# 정규식으로 고급 교체
result = hwp_find_replace_all_advanced(
    find_text=r"\d+",  # 숫자 매칭
    replace_text="[숫자]",
    regex=True
)
```

### 텍스트 서식 지정

```python
hwp_connect()
hwp_create()

# 글꼴 설정
hwp_set_font(font_name="NanumGothic", size=16, bold=True)

# 제목 삽입
hwp_insert_text("문서 제목\n\n")

# 서식 초기화
hwp_set_font(font_name="NanumGothic", size=12)

# 본문 삽입
hwp_insert_text("이것은 본문 텍스트입니다.")

# 선택 영역에서 진하게 토글
hwp_toggle_bold()
```

### HWP SDK 확장 기능 (Windows)

```python
hwp_connect()
hwp_create()

# Actions.h의 액션 실행 (800개 이상 사용 가능)
hwp_run_action(action_id="CharShapeBold")  # 진하게 토글
hwp_run_action(action_id="ParagraphShapeAlignCenter")  # 가운데 정렬

# 페이지 설정 (A4, Letter, 여백, 방향)
hwp_page_setup(
    paper_type="a4",
    orientation="portrait",
    top_margin_mm=25,
    bottom_margin_mm=25,
    left_margin_mm=30,
    right_margin_mm=30
)

# 쪽 번호 삽입
hwp_insert_page_number(
    position=4,  # 4=하단 가운데
    number_format=0,  # 0=아라비아 숫자 (1, 2, 3...)
    starting_number=1,
    side_char="-"  # 결과: "- 1 -"
)

# 표 셀 서식 지정 (먼저 셀 선택 필요)
hwp_table_format_cell(
    fill_color=0xFFFF00,  # 노란색
    border_type=1,  # 실선
    border_width=5  # 0.5mm
)

# 정밀 커서 이동
hwp_move_to(move_id="MoveDocEnd")  # 문서 끝으로 이동
hwp_move_to(move_id="MoveParaBegin")  # 문단 시작으로 이동

# 텍스트 범위 선택
hwp_select_range(
    start_para=0, start_pos=0,
    end_para=0, end_pos=10
)

# 머리말/꼬리말 삽입
hwp_insert_header_footer(
    header_or_footer="header",
    content="회사명 - 대외비"
)

# 각주 삽입
hwp_insert_note(
    note_type="footnote",
    content="참고: HWP SDK 문서"
)

# 문서 모드 설정
hwp_set_edit_mode(mode="readonly")  # readonly, edit, form

# 메타태그 관리 (숨겨진 메타데이터)
hwp_manage_metatags(action="set", tag_name="author", tag_value="AI Assistant")
hwp_manage_metatags(action="list")  # 모든 태그 가져오기

# 배경 이미지 삽입
hwp_insert_background(
    image_path="background.png",
    embedded=True,
    fill_option="tile"  # tile, center, stretch, fit
)

# 책갈피 및 하이퍼링크 삽입
hwp_insert_bookmark(name="section1")
hwp_insert_hyperlink(url="https://example.com", display_text="웹사이트 방문")

# 표 작업 (나누기/합치기)
# 커서가 셀 안에 있다고 가정
hwp_table_split_cell(rows=2, cols=2)

# 셀이 선택되어 있다고 가정
hwp_table_merge_cells()

hwp_save_as(path="advanced_document.hwp")
```

### 고급 자동화 시나리오

여러 기능을 결합하여 구조화된 보고서를 생성하는 예제입니다.

```python
hwp_connect()
hwp_create()

# 1. 페이지 설정
hwp_page_setup(paper_type="a4", orientation="portrait", top_margin_mm=20)

# 2. 제목 추가 및 책갈피 설정
hwp_set_font(font_name="맑은 고딕", size=24, bold=True)
hwp_insert_text("월간 보고서\n")
hwp_insert_bookmark(name="top")  # 탐색용 책갈피
hwp_insert_text("\n")

# 3. 요약 섹션 추가
hwp_set_font(font_name="맑은 고딕", size=14, bold=True)
hwp_insert_text("1. 요약\n")
hwp_set_font(font_name="맑은 고딕", size=11, bold=False)
hwp_insert_text("이 보고서는 주요 성과 지표를 요약합니다.\n")
hwp_insert_text("자세한 내용은 ")
hwp_insert_hyperlink(url="https://dashboard.example.com", display_text="대시보드")
hwp_insert_text("를 참조하세요.\n\n")

# 4. 데이터 표 생성
hwp_set_font(font_name="맑은 고딕", size=14, bold=True)
hwp_insert_text("2. 데이터 표\n")
hwp_create_table(rows=4, cols=3)

# 헤더 작성
hwp_set_cell_text(row=0, col=0, text="지표")
hwp_set_cell_text(row=0, col=1, text="목표")
hwp_set_cell_text(row=0, col=2, text="실적")

# 헤더 서식 (노란색 배경)
# 참고: 각 셀로 이동 필요
hwp_goto_cell("A1")
hwp_table_format_cell(fill_color=0xFFFF00)
hwp_goto_cell("B1")
hwp_table_format_cell(fill_color=0xFFFF00)
hwp_goto_cell("C1")
hwp_table_format_cell(fill_color=0xFFFF00)

# 5. 셀 나누기를 통한 상세 메모
hwp_move_to(move_id="MoveDocEnd")
hwp_insert_text("\n\n비고:\n")
hwp_create_table(rows=1, cols=1)
hwp_table_split_cell(rows=2, cols=1)  # 셀을 2행으로 나누기
hwp_set_cell_text(row=0, col=0, text="비고 1: 시장 상황 안정적.")
hwp_set_cell_text(row=1, col=0, text="비고 2: 3분기 전망 업데이트됨.")

# 6. 꼬리말 추가
hwp_insert_header_footer(header_or_footer="footer", content="대외비 - 사내 열람용")

hwp_save_as("monthly_report.hwp")
```


### 템플릿 사용 (Using Templates)

내장된 HWPX 템플릿을 사용하여 문서를 생성할 수 있습니다.

#### 템플릿 갤러리

| ID | 이름 | 카테고리 | 설명 |
|----|------|----------|------|
| `h01_career_resume` | Career Resume | 이력서 | 이력서 및 자기소개서 템플릿 |
| `h02_basics_report1` | Basics Report1 | 보고서 | 기본 보고서/초안 템플릿 |
| `h03_hard_report2` | Hard Report2 | 보고서 | 표준 비즈니스 보고서 템플릿 |
| `h04_very_hard_report3` | Very Hard Report3 | 보고서 | 상세 심층 보고서 템플릿 |
| `h05_dissertation` | Dissertation | 학술 | 논문/학술서 템플릿 |
| `h06_project_proposal` | Project Proposal | 제안서 | 프로젝트 기획/제안서 템플릿 |

#### 템플릿 미리보기
템플릿 내용을 확인하려면 PDF나 HTML로 내보내어 볼 수 있습니다:

```python
# 템플릿을 PDF로 미리보기
hwp_export_pdf(source_path="templates/h01_career_resume.hwpx", output_path="preview.pdf")
```

#### 문서 생성 예시
```python
# 템플릿으로 이력서 생성
hwp_create_from_template(
    template_id="h01_career_resume",
    save_path="my_resume.hwpx",
    data={
        "name": "홍길동",
        "phone": "010-1234-5678",
    }
)
```

## 플랫폼별 차이점

| 기능 | Windows (COM) | macOS/Linux (python-hwpx) |
|------|---------------|---------------------------|
| 기존 HWP 편집 | ✅ 전체 지원 | ❌ 읽기 전용 |
| 새 HWPX 생성 | ✅ 전체 지원 | ✅ 전체 지원 |
| 표 | ✅ 모든 기능 | ✅ 기본 기능 |
| 차트 | ✅ 모든 기능 | ✅ 생성만 |
| 수식 | ✅ 모든 기능 | ✅ 생성만 |
| 필드 | ✅ 전체 지원 | ❌ 미지원 |
| 서식 | ✅ 전체 제어 | ✅ 기본 제어 |
| SDK 확장 기능 (Actions, PageSetup 등) | ✅ 전체 지원 | ❌ 미지원 |

## 요구사항

- Python 3.10 이상
- MCP >= 1.0.0
- fastmcp >= 0.2.0
- pyhwp >= 0.1a (비 Windows에서 HWP 읽기용)
- python-hwpx >= 1.9 (HWPX 생성용)
- lxml >= 5.0.0 (XML 처리)
- defusedxml >= 0.7.0 (XML 보안)
- xmlschema >= 3.0.0 (유효성 검사)
- pydantic-xml >= 2.0.0 (객체 매핑)
- xmldiff >= 2.0.0 (스마트 편집)
- pandas >= 2.0.0 (차트 데이터용)
- matplotlib >= 3.7.0 (차트 렌더링용)

### Windows 전용
- pywin32 >= 300 (COM 자동화용)
- 한글 2010 이상

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│              MCP 클라이언트 (Claude 등)           │
└───────────────────┬─────────────────────────────┘
                    │ JSON-RPC
                    ▼
┌─────────────────────────────────────────────────┐
│              HWPX-MCP 서버                       │
│              (src/server.py)                     │
└───────────────────┬─────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌─────────────────┐  ┌─────────────────────┐
│ Windows HWP     │  │ 크로스 플랫폼 HWPX  │
│ 컨트롤러        │  │ 컨트롤러            │
│ (pywin32/COM)   │  │ (python-hwpx)       │
└─────────────────┘  └─────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────┐  ┌─────────────────────┐
│ 한글 오피스     │  │ HWPX 파일 생성       │
│ (Windows 전용)  │  │ (Headless)          │
└─────────────────┘  └─────────────────────┘
```

## 개발

```bash
# 개발 의존성 설치
pip install -e ".[dev]"

# 테스트 실행
pytest hwpx_mcp/tests/ -v

# 서버 실행
python -m hwpx_mcp.server
```

## 라이선스

MIT 라이선스

## 기여

기여는 환영입니다!Pull Request를 자유롭게 제출해 주세요.

## 참고 프로젝트

이 프로젝트는 다음의 훌륭한 라이브러리들과 MCP 서버들을 참고하여 개발되었습니다:

### MCP 서버
- **[Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server)** - Microsoft Word용 MCP 서버. 문서 관리, 콘텐츠 생성, 표 서식, 댓글 등 포괄적인 도구 설계를 참고하여 HWP 문서에서도 동등한 사용자 경험을 제공합니다.

### HWP 자동화 라이브러리
- **[pyhwpx](https://github.com/martiniifun/pyhwpx)** - Windows용 HWP 자동화를 위한 포괄적인 Python 래퍼. pywin32 기반으로 텍스트 삽입, 문서 편집, 서식, 표 등의 고급 API를 제공합니다. 고급 기능 구현의 핵심 참조 자료.
- **[pywin32](https://github.com/mhammond/pywin32)** - COM 자동화를 포함한 Windows API 접근을 제공하는 Python 확장. `win32com`을 통한 Windows HWP 자동화의 기반.
- **[python-hwpx](https://github.com/airmang/python-hwpx)** - HWPX (Open XML) 파일 조작을 위한 Python 라이브러리. HWP 설치 없이 크로스 플랫폼 HWPX 생성에 사용.

### HWP 파일 형식 라이브러리
- **[hwplibsharp](https://github.com/rkttu/hwplibsharp)** - HWP 파일 형식 파싱을 위한 C# 라이브러리.
- **[hwplib](https://github.com/neolord0/hwplib)** - HWP 파일 형식을 위한 Java 라이브러리.
- **[pyhwp](https://github.com/mete0r/pyhwp)** - HWP 바이너리 파일 파싱을 위한 Python 도구.

### 이전 프로젝트
- **[hwp-mcp](https://github.com/jkf87/hwp-mcp)** - 이 확장 버전의 영감이 된 오리지널 HWP MCP 서버.

HWP 생태계에 기여해 주신 이 프로젝트 개발자들에게 특별한 감사를 드립니다.
