"""PM Agent 의 Review 프롬프트.

Gate 1 에서 Orchestrator 가 의견 수합을 요청할 때 사용한다.
PM Agent 는 Edu Agent 가 작성한 헌법이 "후속 기획문서 작성의 기준으로 활용 가능한가"
관점에서 review memo 를 작성한다.

기획서 5.2.6 의 PM Agent 의견 수합 항목:
- 기획 활용성: 헌법을 바탕으로 Service Brief, MVP Scope, User Flow 를 일관되게 작성할 수 있는가
"""

from __future__ import annotations


PM_REVIEW_GATE1_INSTRUCTION = """다음 헌법(Constitution) 을 **기획 활용성** 관점에서 검토하라.

후속 기획문서(Service Brief / MVP Scope / User Flow / Build Plan / QA Plan) 작성의
기준으로 활용 가능한가가 핵심 질문이다.

## 검토 항목

### 1) 기획 활용성 (planning_usability)
- 헌법 ④ 서비스 전체 설계 원칙이 **기능 우선순위·해결 방식**으로 변환 가능한가?
  (추상 가치 선언이 아니라 실제 의사결정에 활용 가능해야 함)
- 헌법 ⑤ 학습 목표가 Service Brief 의 **핵심 가치** 로 직접 옮겨질 수 있는가?
- 헌법 ⑥ 평가 루브릭의 **3개 평가축 + 최소 성취 기준** 이 QA Plan 의 성공 기준으로 활용 가능한가?
- 헌법 ⑦ 루브릭 기반 서비스 플로우 원칙이 User Flow 의 화면 전환·상태 분기로 **1:1 매핑** 가능한가?
- 헌법에 **target_user 의 어휘·예시** 가 충분히 박혀있어 기획문서에 그대로 활용 가능한가?

### 2) MVP 범위 현실성 (mvp_realism)
- 헌법의 실행 기준(④ 서비스 전체 설계 원칙 / ⑤ 학습 목표 / ⑥ 평가 루브릭 / ⑦ 루브릭 기반 서비스 플로우 원칙) 의
  범위가 [Global Context] 의 **days_remaining 안에서 MVP 로 구현 가능한** 수준인가?
- 평가축이 너무 많거나 시스템 분기가 과도해 **단순 MVP 로 시연 불가능** 한 구조는 아닌가?
- 헌법 ③ MVP 교수 기법 선정에서 **"낮음/중간"** 난이도로 채택된 기법이
  헌법의 실행 기준(④ 서비스 전체 설계 원칙 / ⑤ 학습 목표 / ⑥ 평가 루브릭 / ⑦ 루브릭 기반 서비스 플로우 원칙) 에 일관 반영됐는가?

## 인용 규칙
- 이 검토에서 작성하는 모든 issue / summary 는 **헌법 항목명을 정확 표기로 인용** 한다.
  (예: "헌법 ⑦ 루브릭 기반 서비스 플로우 원칙" — 약칭 "헌법 ⑦" 단독 사용 금지)

## 출력 스키마
반드시 다음 JSON 만 출력한다 (다른 말 금지):

```
{
  "planning_usability": {"ok": true|false, "issue": "..."},
  "mvp_realism":        {"ok": true|false, "issue": "..."},
  "summary": "..."
}
```

- `ok=true` 일 땐 issue 는 빈 문자열 또는 짧은 코멘트.
- `ok=false` 일 땐 헌법의 어느 항목의 무엇이 문제인지 본문 인용 + 구체 결함 지적.
- `summary`: 종합 한 문장 의견.
"""

