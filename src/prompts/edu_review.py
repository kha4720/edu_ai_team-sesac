"""Edu Agent 의 Review 프롬프트.

Gate 1/2/3 에서 Team Lead 가 의견 수합을 요청할 때 사용한다.
Edu Agent 는 자기 작성 산출물(헌법) 이 아닌 PM/Tech 산출물에 대해
**헌법 정합성 + 학습 효과성** 관점에서 review memo 를 작성.

기획서 5.3.6 의 Edu Agent 의견 수합 항목:
- 헌법 정합성: ④⑤⑥⑦ 이 산출물에 어긋나지 않는가?
- 학습 효과성: 서비스 전체가 학습 목표 달성 경험으로 이어지는가?

기획서 5.4 의 Edu Agent 의견 수합 항목 (Gate 3):
- 구현 명세서 4종이 헌법 ④~⑦ 을 훼손하지 않는가?
- 헌법의 학습 목표 및 평가 루브릭이 시스템 동작 및 응답 로직에 반영되었는가?
"""

from __future__ import annotations


EDU_REVIEW_GATE2_INSTRUCTION = """다음 기획문서 5종 (Service Brief / MVP Scope / User Flow / Build Plan / QA Plan) 을
**헌법 정합성** 과 **학습 효과성** 두 관점에서 검토하라.

## 검토 항목

### 1) 헌법 정합성 (constitution_alignment)
- Service Brief 의 해결 방식 / 핵심 가치 가 **헌법 ④ 서비스 전체 설계 원칙** 을 반영하는가?
- MVP Scope 의 필수 기능이 **헌법 ④ 서비스 전체 설계 원칙** 의 우선순위와 충돌하지 않는가?
- User Flow 의 화면 전환·피드백 구조가 **헌법 ⑦ 루브릭 기반 서비스 플로우 원칙** 에 부합하는가?
- QA Plan 의 성공 기준이 **헌법 ⑥ 평가 루브릭** 을 기반으로 설정되어 있는가?
- 헌법 ③ 에서 **제외된 교수 기법** 이 5종 문서 어딘가에 다시 등장하지 않는가?

### 2) 학습 효과성 (learning_effectiveness)
- 서비스 전체가 [Global Context] 의 target_user 가 **헌법 ⑤ 학습 목표** 를 달성하는 경험으로 이어지는가?
- 화면 흐름·피드백·QA 항목이 학습자 인지 발달 단계에 적합한가?
- 평가 기준(QA 의 성공 기준)이 단순 클릭/입력만 측정하지 않고 학습 성취를 측정하는가?

## 출력 스키마
반드시 다음 JSON 만 출력한다 (다른 말 금지):

```
{
  "constitution_alignment": {"ok": true|false, "issue": "..."},
  "learning_effectiveness": {"ok": true|false, "issue": "..."},
  "summary": "..."
}
```

- `ok=true` 일 땐 issue 는 빈 문자열 또는 짧은 코멘트.
- `ok=false` 일 땐 어느 문서/어느 부분이 문제인지 본문 인용 + 구체 결함 지적.
- `summary`: 종합 한 문장 의견 (Team Lead 가 종합 판단 시 참고).
"""


EDU_REVIEW_GATE3_INSTRUCTION = """다음 구현 명세서 4종 (Data Schema / State Machine / Prompt Spec / Interface Spec) 을
**헌법 정합성** 과 **학습 로직 반영** 두 관점에서 검토하라.

이 4종은 헌법(Constitution)이 시스템 동작·응답 로직으로 옮겨지는 마지막 변환 단계다.
여기서 헌법이 훼손되면 후속 코드 단계에서 복원 불가능하다.

## 검토 항목

### 1) 헌법 정합성 (constitution_alignment)
- 구현 명세서 4종이 **헌법 ④ 서비스 전체 설계 원칙** 을 훼손하지 않는가?
- **헌법 ⑤ 학습 목표** 가 Prompt Spec 의 시스템 프롬프트·모드별 분기에 반영되어 있는가?
- **헌법 ⑥ 평가 루브릭** 의 평가축 3개가 Data Schema 의 mode enum / Prompt Spec 의 판단 로직에 반영되어 있는가?
- **헌법 ⑦ 루브릭 기반 서비스 플로우 원칙** 의 분기 구조가 State Machine 의 상태 전이로 1:1 변환되어 있는가?
- 헌법 ③ 에서 **제외된 교수 기법** 이 4종 어딘가에 다시 등장하지 않는가?

### 2) 학습 로직 반영 (learning_logic_fit)
- 헌법의 **학습 목표·평가 루브릭** 이 단순한 입력/출력 처리로 환원되지 않고, **학습 성취를 판단하는 로직**으로 명세에 들어와 있는가?
- Prompt Spec 의 모드별 응답이 학습자의 단계적 성취를 유도하는 형태인가? (정답 직접 제시 vs. 발문/되묻기)
- State Machine 의 종료 조건이 단순 "최대 시도 횟수" 가 아니라 **학습 성취 기준** 도 함께 반영하는가?

## 인용 규칙
- 이 검토에서 작성하는 모든 issue / summary 는 **헌법 항목명을 정확 표기로 인용** 한다.
  (예: "헌법 ⑦ 루브릭 기반 서비스 플로우 원칙" — 약칭 "헌법 ⑦" 단독 사용 금지)

## 출력 스키마
반드시 다음 JSON 만 출력한다 (다른 말 금지):

```
{
  "constitution_alignment": {"ok": true|false, "issue": "..."},
  "learning_logic_fit":     {"ok": true|false, "issue": "..."},
  "summary": "..."
}
```

- `ok=true` 일 땐 issue 는 빈 문자열 또는 짧은 코멘트.
- `ok=false` 일 땐 어느 명세서/어느 부분이 문제인지 본문 인용 + 구체 결함 지적.
- `summary`: 종합 한 문장 의견.
"""
