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

## 사용 가능한 도구

### 시스템 및 연결

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_connect` | HWP 컨트롤러에 연결 (Windows COM 또는 크로스 플랫폼 자동 선택) | 전체 |
| `hwp_disconnect` | HWP 컨트롤러 연결 해제 및 리소스 정리 | 전체 |
| `hwp_platform_info` | 현재 플랫폼 정보 및 사용 가능한 HWP 기능 확인 | 전체 |
| `hwp_capabilities` | 지원되는 전체 기능 매트릭스 확인 | 전체 |

### 문서 생명주기

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create` | 새 HWP 문서 생성 | 전체 |
| `hwp_open` | 기존 HWP/HWPX 문서 열기 | 전체 |
| `hwp_save` | 현재 문서 저장 | 전체 |
| `hwp_save_as` | 지정된 형식(hwp, hwpx, pdf)으로 문서 저장 | 전체 |
| `hwp_close` | 현재 문서 닫기 | 전체 |

### 텍스트 및 편집

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_insert_text` | 현재 커서 위치에 텍스트 삽입 | 전체 |
| `hwp_get_text` | 현재 문서에서 전체 텍스트 가져오기 | 전체 |
| `hwp_find` | 문서에서 텍스트 찾기 | 전체 |
| `hwp_find_replace` | 텍스트 찾아 바꾸기 (1회) | Windows |
| `hwp_find_replace_all` | 모든 occurrence 찾아 바꾸기 | Windows |
| `hwp_find_advanced` | 정규식 지원 고급 검색 | Windows |
| `hwp_find_replace_advanced` | 정규식 지원 고급 찾아 바꾸기 | Windows |

### 표 조작

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_table` | 지정된 행과 열로 표 생성 | 전체 |
| `hwp_set_cell_text` | 특정 셀(행, 열)에 텍스트 설정 | 전체 |
| `hwp_get_cell_text` | 특정 셀에서 텍스트 가져오기 | 전체 |
| `hwp_goto_cell` | 특정 셀 주소로 이동 (예: 'A1') | Windows |
| `hwp_get_cell_addr` | 현재 셀 주소 가져오기 (예: 'A1') | Windows |
| `hwp_adjust_cellwidth` | 열 너비 조정 (비율 모드 지원) | Windows |

### 서식 지정

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_set_font` | 글꼴 이름 및 크기 설정 | 전체 |
| `hwp_set_charshape` | 문자 모양 설정 (진하게, 기울임, 밑줄, 색상) | Windows |
| `hwp_get_charshape` | 현재 문자 모양 정보 가져오기 | Windows |
| `hwp_set_parashape` | 문단 모양 설정 (정렬, 줄 간격) | Windows |
| `hwp_toggle_bold` | 진하게 서식 토글 | Windows |
| `hwp_toggle_italic` | 기울임 서식 토글 | Windows |
| `hwp_toggle_underline` | 밑줄 서식 토글 | Windows |
| `hwp_toggle_strikethrough` | 취소선 서식 토글 | Windows |

### 차트

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_chart` | 데이터로 차트 생성 | 전체 |

### 수식

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_equation` | 수학 공식 생성 | 전체 |

### 템플릿

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_create_from_template` | 템플릿 파일에서 문서 생성 | 전체 |
| `hwp_fill_template` | 템플릿 필드에 데이터 채우기 | 전체 |

### 필드 (누름틀)

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_get_field_list` | 모든 필드 이름 목록 가져오기 | Windows |
| `hwp_put_field_text` | 이름으로 필드에 텍스트 설정 | Windows |
| `hwp_get_field_text` | 필드에서 텍스트 가져오기 | Windows |
| `hwp_field_exists` | 필드가 존재하는지 확인 | Windows |
| `hwp_create_field` | 새 필드 생성 | Windows |

### 페이지 및 탐색

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_get_page_count` | 전체 페이지 수 가져오기 | 전체 |
| `hwp_goto_page` | 특정 페이지로 이동 (0 기반) | 전체 |
| `hwp_move_to_start` | 커서를 문서 시작 위치로 이동 | Windows |
| `hwp_move_to_end` | 커서를 문서 끝 위치로 이동 | Windows |
| `hwp_get_page_text` | 특정 페이지에서 텍스트 가져오기 | Windows |

### 유틸리티 도구

| 도구 | 설명 | 플랫폼 |
|------|------|--------|
| `hwp_head_type` | 제목 유형 문자열을 HWP 정수 값으로 변환 | 전체 |
| `hwp_line_type` | 선 유형 문자열을 HWP 정수 값으로 변환 | 전체 |
| `hwp_line_width` | 선 두께 문자열을 HWP 정수 값으로 변환 | 전체 |
| `hwp_number_format` | 숫자 형식 문자열을 HWP 정수로 변환 | 전체 |
| `hwp_convert_unit` | HwpUnit과 mm 간 변환 | 전체 |
| `hwp_get_head_types` | 사용 가능한 제목 유형 가져오기 | 전체 |
| `hwp_get_line_types` | 사용 가능한 선 유형 가져오기 | 전체 |
| `hwp_get_line_widths` | 사용 가능한 선 두께 가져오기 | 전체 |
| `hwp_get_number_formats` | 사용 가능한 숫자 형식 가져오기 | 전체 |

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

## 요구사항

- Python 3.10 이상
- MCP >= 1.0.0
- fastmcp >= 0.2.0
- pyhwp >= 0.1a (비 Windows에서 HWP 읽기용)
- python-hwpx >= 1.9 (HWPX 생성용)
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

## 로드맵 및 예정된 기능

[Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server)의 기능과 [pyhwpx](https://github.com/martiniifun/pyhwpx) ([pywin32](https://github.com/mhammond/pywin32) 기반)의 고급 자동화 기능을 참고하여 HWPX-MCP의 기능을 확장할 계획입니다.

### 1단계: 고급 서식 및 스타일
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **문단 스타일** | 들여쓰기, 줄 간격, 정렬, 탭 설정 | 높음 |
| **글자 스타일** | 글꼴, 크기, 색상, 형광펜, 자간 | 높음 |
| **스타일 관리** | 이름 지정 스타일 적용/관리 (예: "제목 1", "본문") | 중간 |
| **직접 서식** | 콘텐츠 생성 시 글꼴/크기/굵게/기울임 적용 | 높음 |

### 2단계: 페이지 레이아웃 및 구역
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **페이지 설정** | 용지 방향(가로/세로), 여백, 용지 크기 | 높음 |
| **다단 설정** | 다단 레이아웃 생성 및 관리 | 중간 |
| **머리말/꼬리말** | 머리말/꼬리말 편집, 쪽 번호 | 높음 |
| **구역 제어** | 별도 레이아웃의 구역 관리 | 중간 |

### 3단계: 고급 표 기능
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **셀 병합** | 가로, 세로, 사각형 영역 병합 | 높음 |
| **셀 정렬** | 가로/세로 위치 정렬 | 높음 |
| **셀 여백** | 상하좌우 독립 제어 | 중간 |
| **열 너비** | 포인트, 퍼센트, 자동 맞춤 | 중간 |
| **줄무늬 행** | 교대 행 색상 적용 | 낮음 |
| **헤더 강조** | 헤더 행 색상 지정 | 낮음 |

### 4단계: 고급 개체 및 미디어
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **이미지** | 정밀한 크기, 위치, 배치 스타일 | 높음 |
| **도형 및 글상자** | 도형/글상자 삽입 및 서식 | 중간 |
| **하이퍼링크** | 내부 책갈피, 외부 링크 | 중간 |
| **OLE 개체** | 외부 개체 삽입 | 낮음 |

### 5단계: 검토 및 협업 (Windows 전용)
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **메모** | 메모 삽입, 읽기, 삭제 | 높음 |
| **변경 내용 추적** | 추적 활성화/비활성화, 수락/거부 | 중간 |
| **문서 보호** | 암호 보호, 편집 제한 | 낮음 |

### 6단계: 문서 자동화
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **메일 머지** | 고급 필드 매핑, 일괄 생성 | 중간 |
| **차례(목차)** | 제목 기반 목차 자동 생성/업데이트 | 높음 |
| **색인** | 색인 항목 생성 및 페이지 생성 | 낮음 |
| **PDF 변환** | HWP/HWPX를 PDF로 변환 | 높음 |
| **문서 병합** | 여러 문서 병합 | 중간 |

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
