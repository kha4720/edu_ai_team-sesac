"""Tech Agent 의 Review 프롬프트.

Gate 1/2/3 에서 Orchestrator 가 의견 수합을 요청할 때 사용한다.
Tech Agent 는 자기 작성 산출물(Build Plan) 외 산출물에 대해서도
**기술 실행 가능성** 관점에서 review memo 를 작성.

기획서 5.3.6 의 Tech Agent 의견 수합 항목:
- 기술 실행 가능성: MVP Scope 와 User Flow 가 인력·기술 수준으로 구현 가능?
- 구현 계획 타당성: Build Plan 의 모듈/스택/순서가 현실적?

설계 결정 (체크리스트화 롤백):
- worklog 13 에서 deadline 환각이 작성 단계에서 차단되도록 변경 후, 검증자가 산술까지
  체크할 필요가 없어졌다. 체크리스트(7개 CP)가 과도하게 길어 프롬프트 비용/노이즈만 증가.
- 작성 단계에서 days_remaining 이 명시적으로 박혀있으므로, 검증자는 "본문이 그 기준을
  따랐는가" 만 자연어로 판단하면 충분.
"""

from __future__ import annotations


TECH_REVIEW_GATE2_INSTRUCTION = """다음 기획문서 5종 (Service Brief / MVP Scope / User Flow / Build Plan / QA Plan) 을
**기술 실행 가능성** 과 **구현 계획 타당성** 관점에서 검토하라.

너는 Tech Agent 다. 작성자(PM/Tech) 가 아니라 검토자 입장에서 객관적으로 본다.

## 검토 항목

### 1) 기술 실행 가능성 (technical_feasibility)
- [Global Context] 의 **days_remaining** 안에서 5종 문서의 일정·범위가 일관되는가?
  - MVP Scope 의 "기능 개발 순서" 합계가 days_remaining 을 초과하지 않는가?
  - 5종 본문에 "1년 내", "Phase Y", "장기 운영" 같은 추상 기간 표현이 등장하지 않는가?
- team_size 와 Build Plan 의 담당 역할 분배가 현실적인가?
- 기술 스택이 team_capability 와 어긋나지 않는가? (모르는 기술을 단기간에 익혀야 한다면 risk)

### 2) 구현 계획 타당성 (build_plan_validity)
- Build Plan 의 모듈 구성이 User Flow 와 일관되는가? (User Flow 단계마다 대응 모듈이 있는가)
- 필요 API / AI 기능이 입력/출력/목적을 모두 명시하는가?
- 구현 순서가 의존성을 반영하는가? (선행 모듈이 먼저 등장하는가)
- 완료 기준이 시연 가능 여부와 핵심 기능 동작 여부 중심인가?

## 출력 스키마
반드시 다음 JSON 만 출력한다 (다른 말 금지):

```
{
  "technical_feasibility": {"ok": true|false, "issue": "..."},
  "build_plan_validity":   {"ok": true|false, "issue": "..."},
  "summary": "..."
}
```

- `ok=true` 일 땐 issue 는 빈 문자열 또는 짧은 코멘트.
- `ok=false` 일 땐 어느 문서/어느 부분이 문제인지 본문 인용 + 구체 결함 지적.
- `summary`: 종합 한 문장 의견.
"""


TECH_REVIEW_SYSTEM_OVERRIDE_TAIL = """

## Review 모드
지금 너는 산출물 작성이 아니라 **검토(review)** 모드다.
- JSON 으로만 응답한다. 다른 텍스트 절대 금지.
- 작성자의 입장에서 변호하지 마라. 본질에서 결함이 있는가만 본다.
- 사소한 문체 차이는 issue 가 아니다.
- [Global Context] 의 days_remaining 숫자를 그대로 기준으로 쓴다 (직접 산술 금지).
"""