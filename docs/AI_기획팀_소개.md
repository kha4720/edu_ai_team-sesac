# AI 기획팀 — 기획 문서 하네스 소개

> **한 줄 정의:** 교육 서비스 기획자가 아이디어와 실행 제약을 입력하면, AI 에이전트 팀이 협업하여 **서비스 원칙서 · 기획문서 5종 · 구현 명세서 4종**을 자동 생성하는 멀티에이전트 하네스.

---

## 1. 기획 의도

### 왜 만들었는가

교육 서비스 MVP를 기획할 때 반복되는 문제가 있다.

- 좋은 아이디어가 있어도 **교육공학적 근거 없이** 기획이 진행된다
- 서비스 기획, 개발 계획, 구현 명세가 **각자 다른 가정** 위에서 만들어진다
- AI 기반 서비스를 만들려면 기획 문서 외에 **LLM 실행 가능한 프롬프트 명세**까지 필요하다
- 이 모든 걸 사람이 순서대로 만들기엔 시간과 전문성이 동시에 요구된다

이 하네스는 그 공백을 채운다. 기획자는 아이디어와 제약만 입력하면, AI 에이전트 팀이 교육공학 기반으로 기획을 정립하고, 기획자·개발자·AI 모두가 읽을 수 있는 문서 패키지를 생산한다.

### 설계 원칙

1. **교육공학 우선**: 모든 문서는 서비스 원칙서(교수 설계서)로부터 흘러나온다. 원칙서가 후속 문서의 타당성 판단 기준이 된다.
2. **정합성 보장**: 에이전트마다 독립적으로 작성하면 문서 간 충돌이 생긴다. 3단계 Gate 검증으로 산출물 간 논리적 정합성을 검증한다.
3. **실행 가능한 산출물**: 사람이 읽는 문서(기획문서 5종)와 AI가 실행할 수 있는 문서(구현 명세서 4종)를 함께 생산한다.
4. **환각 차단 설계**: LLM의 산술 환각을 막기 위해 `days_remaining`(남은 일수)을 입력 단계에서 미리 계산해 모든 에이전트 프롬프트에 명시한다.

---

## 2. 시스템 구성

### 2.1 에이전트 구성

| 에이전트 | 역할 | 주요 산출물 |
|---------|------|-----------|
| **Team Lead** (Orchestrator) | 전 공정 제어, Gate 최종 결정, 에이전트 간 업무 배정 | Gate 1 · 2 · 3 검증 결과 |
| **Edu Agent** | 교육공학 기반 서비스 설계, 학습 효과와 UX를 동시에 판단하는 교육 기획 전문가 | 서비스 원칙서 (헌법) |
| **PM Agent** | 서비스 기획·문서화·요구사항 정의 전문가 | 기획문서 4종 + 구현 명세서 3종 |
| **Tech Agent** | 기술적 구현 가능성과 품질을 동시에 책임지는 테크 리더 | Build Plan + Gate 기술 검토 |
| **Prompt Agent** | 서비스 원칙서를 LLM이 실행할 수 있는 언어로 번역하는 프롬프트 엔지니어링 전문가 | Prompt Spec |

### 2.2 전체 워크플로우

```
[1단계] 사용자 입력
  • 서비스 기획 정보: 타깃 유저 / 문제 상황 / 서비스 목표 / 솔루션 아이디어
  • 실행 제약 정보: 마감 기한 / 팀원 구성 / 기술 수준 / 기존 보유 자산
        │
        ▼
[2단계] 서비스 원칙서 작성 — Edu Agent
  • 교육공학적 문제 재정의 (①)
  • 교수 기법 탐색·비교·선택 (②③)
  • 서비스 전체 설계 원칙 (④)        ← 이하 4개가 핵심 헌법 본체
  • 학습 목표 (⑤)
  • 평가 루브릭 (⑥)
  • 루브릭 기반 서비스 플로우 (⑦)
        │
   [Gate 1] Team Lead + PM + Tech ─── FAIL 시 최대 1회 재작성
        │ PASS
        ▼
[3단계] 기획문서 5종 작성 — PM Agent (4종) + Tech Agent (1종)
  service_brief → mvp_scope → user_flow → build_plan → qa_plan
        │
   [Gate 2] Team Lead + Edu + Tech ─── FAIL 시 최대 1회 재작성
        │ PASS
        ▼
[4단계] 구현 명세서 4종 작성 — PM Agent (3종) + Prompt Agent (1종)
  data_schema → ┬─ state_machine   ← 병렬 실행
                └─ prompt_spec     ← 병렬 실행
                        │
                  interface_spec
        │
   [Gate 3] Team Lead + Tech + Edu ─── FAIL 시 최대 1회 재작성
        │ PASS
        ▼
   완료 — 10종 문서 패키지 생성
```

**컨텍스트 참조 원칙:**
- 모든 에이전트는 직전 산출물뿐 아니라 **사용자 입력 + 서비스 원칙서**를 Global Context로 함께 참조한다
- 이를 통해 사용자 원 요구사항 보존, 산출물 간 논리 정합성, 교육 목표 일관성을 유지한다

### 2.3 Gate 검증 구조

| Gate | 검증 대상 | 검증자 | 검증 항목 |
|------|---------|--------|---------|
| **Gate 1** | 서비스 원칙서 | Team Lead + PM + Tech | 완전성(④~⑦ 모두 작성) / 상위 기준 일관성 / 내부 연계성 / 근거 타당성 |
| **Gate 2** | 기획문서 5종 | Team Lead + Edu + Tech | 완전성 / 유효성(목적 부합) / 정합성(문서 간 충돌 없음) / 진행성(다음 단계 준비) |
| **Gate 3** | 구현 명세서 4종 | Team Lead + Tech + Edu | data_schema 완전성 / state_machine 정합성 / prompt_spec 커버리지 / interface_spec 정렬 |

**Gate 판정 방식:**
- **PASS**: 다음 단계 진행
- **FAIL**: Feedback Memo 작성 → 담당 에이전트 재작성 → 동일 Gate 재검증 (최대 1회)
- **CONDITIONAL_PASS**: 2회 연속 FAIL 시 Risk Memo를 남기고 진행 (실패를 묻지 않음)

Gate fail 후 재작성 분기는 LangGraph `conditional_edges`로 그래프 자체가 표현한다.

---

## 3. 산출물 10종

### 3.1 서비스 원칙서 (1종)

| 파일 | 작성자 | 내용 |
|------|--------|------|
| `constitution.md` | Edu Agent | 교육 설계 원칙서. 후속 9종 문서의 타당성 판단 기준 |

**핵심 구조 (7개 항목):**

| 항목 | 내용 |
|-----|------|
| ① 교육공학적 문제 재정의 | 사용자 입력의 문제를 교육공학 관점으로 재해석 |
| ② 교수 기법 탐색·비교 | 적용 가능한 교수 기법 후보 분석 |
| ③ 선택된 기법 + 근거 | 채택·제외 기법과 이유 |
| **④ 서비스 전체 설계 원칙** | 선택된 교수 기법의 핵심 원리를 서비스 동작 철학으로 번역 |
| **⑤ 학습 목표** | 타깃 유저가 이 서비스를 통해 달성해야 할 상태 |
| **⑥ 평가 루브릭** | 학습 목표 달성 수준을 실시간으로 판단하는 기준 |
| **⑦ 루브릭 기반 서비스 플로우** | 루브릭 판단 결과에 따라 서비스가 어떻게 동작하는가 |

> ④~⑦이 헌법의 핵심 본체. Gate와 모든 후속 에이전트가 이 4개를 기준으로 판단한다.

### 3.2 기획문서 5종 (사람용 문서)

| 파일 | 작성자 | 내용 |
|------|--------|------|
| `service_brief.md` | PM | 서비스 한눈에 이해되는 1장 요약 |
| `mvp_scope.md` | PM | 실행 제약 우선 반영. 구현할 기능 vs 제외 기능 |
| `user_flow.md` | PM | 화면 흐름 + 전환 조건 (6단계 흐름) |
| `build_plan.md` | Tech | LLM API 전제의 개발 계획 + 기술 스택 + 모듈 구조 |
| `qa_plan.md` | PM | 테스트 시나리오 + 성공 기준 |

### 3.3 구현 명세서 4종 (AI용 문서)

| 파일 | 작성자 | 내용 |
|------|--------|------|
| `data_schema.json` | PM | 입출력 필드 규격 (JSON 형식, 파싱 가능) |
| `state_machine.md` | PM | 상태 전이 + mode 매핑 (data_schema의 mode 값과 일치) |
| `prompt_spec.md` | Prompt | 헌법 ④⑤⑥⑦을 LLM이 실행 가능한 시스템 프롬프트로 번역 + Few-shot |
| `interface_spec.md` | PM | API · UI · 모듈 계약서 (User Flow와 정렬) |

**prompt_spec 변환 원칙:**

| 헌법 항목 | prompt_spec 변환 |
|---------|----------------|
| ④ 서비스 전체 설계 원칙 | Constraints (시스템 제약) |
| ⑤ 학습 목표 | Role (LLM 역할 정의) |
| ⑥ 평가 루브릭 | 판단 로직 (모드 분기 조건) |
| ⑦ 루브릭 기반 서비스 플로우 | 모드별 분기 + Few-shot 예시 |

---

## 4. 핵심 설계 결정

### 4.1 Edu Agent의 5단계 분리 호출

서비스 원칙서 작성은 5회 LLM 호출로 구성된다.
- **1회 호출**: ①~③ (설계 근거 3단계를 묶어서) — 컨텍스트 연속성 확보
- **4회 호출**: ④~⑦ (헌법 본체 4개를 각각) — 형식 강제 + 단계별 품질 유지

각 단계는 이전 단계 출력을 Primary Input으로 받아 논리적 연속성을 유지한다.

### 4.2 환각 차단 (Shift-Left)

LLM의 날짜 산술 환각을 방지하기 위해 검증 단계가 아닌 **작성 단계에서** 차단한다.

```python
# 입력 수집 시 days_remaining 미리 계산
days_remaining = (deadline - today).days

# 모든 에이전트 프롬프트에 이 숫자를 명시
# "남은 일수: 12일. 직접 산술하지 말고 이 숫자를 그대로 사용하라."
```

### 4.3 LLM 서비스 대전제 에이전트 페르소나에 명시

이 하네스는 "LLM API를 활용하는 AI 교육 서비스"를 설계한다. 이 대전제를 코드 구조가 아닌 **각 에이전트의 시스템 프롬프트(페르소나)에 직접 명시**한다.

이유: 명시하지 않으면 Tech Agent가 팀 역량·현실성 판단으로 "LLM 미사용, 정규표현식 기반" 방향을 독립적으로 선택할 수 있다. 실제로 발생했던 문제다.

### 4.4 Step 4 병렬 실행

`data_schema` 완료 후 `state_machine`과 `prompt_spec`은 서로 의존성이 없으므로 LangGraph 팬아웃/팬인으로 병렬 실행한다. `interface_spec`은 `state_machine`을 참조하므로 그 후 순차 실행.

```
data_schema → ┬─ state_machine ─┐
              └─ prompt_spec ───┤
                                └─ interface_spec
```

### 4.5 Gate retry는 노드에서, 라우팅은 verdict 값만

Gate 노드 내부에서 retry를 처리하고 `verdict`를 덮어쓴다. 라우터는 `verdict` 값만 보고 다음 노드를 결정한다. 책임을 분리함으로써 라우팅 로직을 단순하게 유지한다.

---

## 5. 검증 사례 — Question Coach MVP

### 5.1 검증 목적

하네스의 실효성을 검증하기 위해 **"중학생 질문력 향상 챗봇"**을 사례 과제로 선정했다.

하네스로 문서를 생산하고, 그 문서를 바탕으로 실제 동작하는 MVP를 구현한 뒤, 기획 문서의 **현실성과 구현 가능성**을 검증했다.

### 5.2 입력 예시

```json
{
  "service": {
    "target_user": "AI를 공부에 활용하지만 질문을 잘 못하는 중학생",
    "problem": "막연한 질문을 입력해 원하는 답을 얻지 못하고 AI 활용 효율이 낮다.",
    "goal": "학생의 질문 품질을 높여 AI 학습 활용 효율을 향상한다.",
    "solution": "질문 코칭 챗봇 MVP"
  },
  "constraints": {
    "deadline": "2026-05-01",
    "team_size": 3,
    "team_capability": "교육 기획 강점 / 프론트 기초 가능 / 개발 이해도 중간",
    "existing_assets": "기획 문서 초안 있음 / 기능 정의 문서 있음 / 코드베이스 없음"
  }
}
```

### 5.3 MVP 구현 검증 결과

| 검증 항목 | 결과 | 발견 사항 |
|---------|------|---------|
| Interface Spec 정렬 | ✓ | `/api/generate-question`, `/api/evaluate-purpose` 실제 구현 확인 |
| State Machine 정합성 | ✓ | User Flow 6단계와 상태 일치 확인 |
| Build Plan 현실성 | △ | "Backend: 없음" 명시 → 실제론 API 키 보호를 위해 Express 백엔드 필수 |

> **핵심 통찰**: 기획 문서만으로는 발견하기 어려운 실제 구현 이슈를 MVP 구현을 통해 조기 발견했다. 하네스가 생산한 문서의 현실성 검증 역할을 수행했다.

### 5.4 MVP 기술 스택

- **백엔드**: Express.js (Node.js) — API 키 보호, Solar API 프록시
- **프론트엔드**: HTML/CSS/JavaScript — 상태 머신 기반 UI 흐름
- **LLM**: Upstage Solar-pro2 API
- **세션 관리**: localStorage 기반 세션 복원

---

## 6. 구현 현황

### 완료

- [x] 멀티에이전트 아키텍처 (Edu / PM / Tech / Prompt / Team Lead)
- [x] LangGraph `conditional_edges` 기반 Gate fail → 재작성 분기
- [x] Gate 1 / 2 / 3 다중검증자 (Team Lead + 전문 에이전트 2명)
- [x] Step 4 병렬 실행 (state_machine + prompt_spec)
- [x] 환각 차단 (`days_remaining` 미리 계산 + 에이전트 페르소나에 LLM 전제 명시)
- [x] Streamlit 데모 UI (입력 → 실행 → 산출물 실시간 표시)
- [x] Question Coach MVP 프로토타입 구현 및 문서 검증

### 발표 후 추가 작업 예정 (`_TODO.md` 기준)

| 우선순위 | 항목 |
|---------|------|
| 0 | State에 토큰 사용량 · 호출 시간 메타 정보 추가 |
| 1 | Gate 1 "의도적 결함 헌법"으로 fail 케이스 검증 |
| 1 | 다른 산출물(service_brief / user_flow / qa_plan)의 환각 점검 |
| 2 | Build Plan 기반 조건부 Prompt Agent 실행 (LLM 없는 서비스 분기) |
| 2 | 웹서치 도구 통합 (Edu Agent 교수 기법 탐색에 실시간 검색 추가) |
| 3 | 멀티 모델 전환 기능 (OpenAI / Anthropic 등 어댑터) |
| 4 | 타입 체크 (mypy) + 단위 테스트 (pytest) |

---

## 7. 기술 스택

| 역할 | 기술 |
|------|------|
| 워크플로우 그래프 | LangGraph (conditional_edges, 팬아웃/팬인) |
| LLM | Upstage Solar-pro2 (OpenAI 호환 API) |
| 스키마 검증 | Pydantic v2 |
| 데모 UI | Streamlit |
| 패키지 관리 | uv |
| 런타임 | Python 3.11+ |

---

## 8. 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. .env 작성
cp .env.example .env
# UPSTAGE_API_KEY 값 입력

# 3. 데모 UI 실행
uv run streamlit run app.py
# → http://localhost:8501

# 4. Solar API 연결 확인
uv run python -m src.llm._test_solar
```

---

## 9. 프로젝트 구조

```
edu_design_harness_project/
├── app.py                  ← Streamlit 데모 UI
├── src/
│   ├── graph.py            ← LangGraph 워크플로우 (13노드 + conditional_edges)
│   ├── runner.py           ← 파이프라인 진입점
│   ├── agents/             ← Edu / PM / Tech / Prompt 에이전트 (4개)
│   ├── gates/              ← Gate 1 / 2 / 3 검증 함수 (3개)
│   ├── schemas/            ← Pydantic 스키마 (입력 / 워크플로우 / 산출물 메타)
│   ├── prompts/            ← 에이전트별 시스템·지시·리뷰 프롬프트 (~30개)
│   └── llm/                ← Solar API 래퍼 + 프롬프트 조립 헬퍼
├── inputs/                 ← 사용자 입력 JSON (검증 케이스)
├── outputs/                ← 실행 결과 산출물 (타임스탬프별 폴더)
├── mvp/                    ← Question Coach MVP 프로토타입 (JS)
├── docs/                   ← 기획서 원안 + 워크플로우 다이어그램
└── worklog/                ← 단계별 개발 기록 (30개)
```

---

*마지막 업데이트: 2026-04-30 | 개발 기록은 [worklog/](../worklog/) 참고*
