"""Data Schema 작성 지시문.

기획서 5.4 / artifact_schema.DATA_SCHEMA 기준. PM Agent 가 사용한다.
"""

from __future__ import annotations


DATA_SCHEMA_INSTRUCTION = """**Data Schema** 를 작성한다.

## 한 줄 정의
MVP 기능 구현에 필요한 입력·출력 데이터 구조와 필드 규격 (JSON 형식).

## 작성 원칙
- MVP 구현에 필요한 **최소 필드만** 정의한다. 추측성 필드는 추가하지 않는다.
- [Primary Inputs] 의 MVP Scope 필수 기능과 User Flow 입력/출력을 직접 매핑해 필드를 도출한다.
- **헌법 ⑦ 루브릭 기반 서비스 플로우 원칙** 에서 시스템 판단(양호/미흡 등)을 `output.mode` 필드로 표현한다.
  - `mode` 는 시스템이 사용자의 응답·입력을 평가해 분기하는 핵심 필드다.
  - 헌법 ⑦에서 정의한 판단 분기를 mode 값(예: "양호", "미흡", "재도전")으로 열거한다.
- 각 필드는 반드시 `type` / `required` / `description` / `example` / `source` 를 포함한다.
  - `source`: 이 필드가 어디서 유래했는지 (예: "User Flow 화면 2", "헌법 ⑦ 판단 분기")

## 출력 구조 (정확히 이 구조를 따름)
```json
{
  "input": {
    "<필드명>": {
      "type": "string | number | boolean | array | object",
      "required": true | false,
      "description": "...",
      "example": "...",
      "source": "..."
    }
  },
  "output": {
    "<필드명>": {
      "type": "...",
      "required": true | false,
      "description": "...",
      "example": "...",
      "source": "..."
    },
    "mode": {
      "type": "string",
      "required": true,
      "description": "시스템 판단 결과 — 헌법 ⑦ 루브릭 기반 분기값",
      "example": "(헌법 ⑦ 판단 분기 중 하나)",
      "enum": ["(헌법 ⑦ 판단 분기값 1)", "(판단 분기값 2)", "..."],
      "source": "헌법 ⑦ 루브릭 기반 서비스 플로우 원칙"
    }
  }
}
```
"""


DATA_SCHEMA_OUTPUT_HINT = """순수 JSON 만 출력한다.
- 코드블록(```json ... ```) 을 사용하지 않는다.
- 여는 중괄호 { 로 시작해 닫는 중괄호 } 로 끝난다.
- 최상위 키는 반드시 "input" 과 "output" 두 개다.
- output 에는 반드시 "mode" 필드가 포함된다.
- 각 필드 객체에 type / required / description / example / source 가 모두 있어야 한다.
- 한국어 설명은 description / example 값으로 포함한다."""