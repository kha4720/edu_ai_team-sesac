# Edu Design Harness

> 교육 서비스 기획자가 아이디어와 실행 제약을 입력하면, LLM 에이전트들이 협업해
> 헌법 · 기획문서 5종 · 구현 명세서 4종을 자동 생성하는 멀티에이전트 하네스.

## 산출 흐름

```
사용자 입력 (서비스 기획 정보 + 실행 제약)
        │
        ▼
[Step 2] Edu Agent  ──▶  constitution.md
        │
   Gate 1 (Team Lead) ── FAIL 시 최대 1회 재작성
        ▼
[Step 3] PM / Tech  ──▶  service_brief.md / mvp_scope.md / user_flow.md
                         build_plan.md / qa_plan.md
        │
   Gate 2 (Team Lead + Edu + Tech 다중 검증) ── FAIL 시 최대 1회 재작성
        ▼
[Step 4] PM / Prompt ──▶  data_schema.json
                          ├─(병렬)─ state_machine.md
                          └─(병렬)─ prompt_spec.md
                          └──────── interface_spec.md
        │
   Gate 3 (Team Lead + Tech + Edu 다중 검증) ── FAIL 시 최대 1회 재작성
        ▼
       완료 (헌법 1종 + 기획문서 5종 + 구현 명세서 4종)
```

## 에이전트 구성

| 에이전트 | 책임 산출물 |
|---------|------------|
| **Edu Agent** | constitution (헌법) |
| **PM Agent** | service_brief / mvp_scope / user_flow / qa_plan / data_schema / state_machine / interface_spec |
| **Tech Agent** | build_plan |
| **Prompt Agent** | prompt_spec |
| **Team Lead** | Gate 1 · 2 · 3 검증 총괄 |

## Gate 검증 구조

| Gate | 대상 | 검증자 | 검증 항목 |
|------|------|--------|---------|
| Gate 1 | 헌법 | Team Lead + PM + Tech | 완전성 / 상위 기준 일관성 / 내부 연계성 / 근거 타당성 |
| Gate 2 | 기획문서 5종 | Team Lead + Edu + Tech | 완전성 / 유효성 / 정합성 / 진행성 |
| Gate 3 | 구현 명세서 4종 | Team Lead + Tech + Edu | data_schema 완전성 / state_machine 정합성 / prompt_spec 커버리지 / interface_spec 정렬 |

각 Gate 는 FAIL 시 작성 노드로 되돌아가는 LangGraph `conditional_edges` 로 구현.
2회차도 FAIL 이면 `CONDITIONAL_PASS` 로 덮어쓰고 `risk_memo` 를 남긴 뒤 진행.

## 산출물 목록

| 단계 | 파일 | 내용 |
|------|------|------|
| Step 2 | `constitution.md` | 교육 설계 헌법 (학습 목표 · 루브릭 · 플로우 원칙) |
| Step 3 | `service_brief.md` | 서비스 1장 요약 |
| | `mvp_scope.md` | 구현 범위 · 제외 기능 |
| | `user_flow.md` | 화면 흐름 · 전환 조건 |
| | `build_plan.md` | 개발 계획 · 모듈 구조 |
| | `qa_plan.md` | 테스트 시나리오 · 성공 기준 |
| Step 4 | `data_schema.json` | 입출력 필드 규격 |
| | `state_machine.md` | 상태 전이 · mode 매핑 |
| | `prompt_spec.md` | LLM 시스템 프롬프트 설계서 |
| | `interface_spec.md` | API · UI · 모듈 계약서 |

## 검증 케이스

기획서 4.1 의 **"중학생 질문력 향상 챗봇"** 을 기본 검증 케이스로 사용 (`inputs/question_coach.json`).

## 기술 스택

- Python 3.11+
- [Upstage Solar API](https://console.upstage.ai/) (OpenAI 호환)
- Pydantic v2 (스키마 / 검증)
- LangGraph (워크플로우 그래프 + conditional_edges)
- Streamlit (데모 UI)
- uv (패키지 / 가상환경 관리)

## 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. .env 작성
cp .env.example .env
# UPSTAGE_API_KEY 값 입력

# 3. 데모 UI 실행
uv run streamlit run app.py
# → http://localhost:8501 접속

# 4. Solar API 연결만 확인하고 싶을 때
uv run python -m src.llm._test_solar
```

## 폴더 구조

```
project/
├── app.py              ← Streamlit 데모 UI
├── src/
│   ├── graph.py        ← LangGraph 워크플로우 정의
│   ├── runner.py       ← 파이프라인 진입점
│   ├── agents/         ← Team Lead / Edu / PM / Tech / Prompt 에이전트
│   ├── schemas/        ← Pydantic 스키마 (입력 / 워크플로우 / 산출물)
│   ├── prompts/        ← 각 에이전트 · Gate 시스템 프롬프트
│   ├── gates/          ← Gate 1 · 2 · 3 검증 함수
│   └── llm/            ← Solar API 호출 래퍼
├── inputs/             ← 사용자 입력 JSON
├── outputs/            ← 실행 결과 산출물
├── docs/               ← 기획서 원안
└── pyproject.toml
```

## 기획 문서

상세 기획서는 [`docs/기획서_원안.md`](docs/기획서_원안.md) 참고.

## 라이선스

MIT
