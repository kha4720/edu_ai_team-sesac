# Edu Design Harness

> 교육 서비스 기획자가 아이디어와 실행 제약을 입력하면, LLM 에이전트들이 협업해 헌법·기획문서·구현명세를 자동 생성하는 멀티에이전트 하네스.

## 산출 흐름

### 현재 구현

```
사용자 입력 (서비스 기획 정보 + 실행 제약)
        │
        ▼
[Step 1] Edu Agent  ──▶  constitution.md
        │
   Gate 1 검증 (Orchestrator) — FAIL 시 최대 1회 재작성
        ▼
[Step 2] PM / Tech ──▶  service_brief.md / mvp_scope.md / user_flow.md
                        build_plan.md / qa_plan.md
        │
   Gate 2 검증 (Orchestrator + Edu + Tech 다중 검증) — FAIL 시 최대 1회 재작성
        ▼
       완료 (헌법 1종 + 기획문서 5종)
```

### 최종 목표

```
        ... Gate 2 통과
        ▼
[Step 3] PM / Prompt ─▶ data_schema.json / state_machine.md
                        prompt_spec.md / interface_spec.md
        │
   Gate 3 검증
        ▼
       완료 (헌법 1종 + 기획문서 5종 + 구현명세 4종)
```

## 검증 케이스

기획서 4.1 의 **"중학생 질문력 향상 챗봇"** 을 첫 검증 케이스로 사용 (`inputs/question_coach.json`).

## 기술 스택

- Python 3.11+
- [Upstage Solar API](https://console.upstage.ai/) (OpenAI 호환)
- Pydantic v2 (스키마/검증)
- LangGraph (워크플로우 그래프)
- Streamlit (데모 UI)
- uv (패키지/가상환경 관리)

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
├── app.py           ← Streamlit 데모 UI
├── src/
│   ├── graph.py     ← LangGraph 워크플로우 정의
│   ├── runner.py    ← 파이프라인 진입점
│   ├── agents/      ← Edu / PM / Tech 에이전트
│   ├── schemas/     ← Pydantic 스키마 (입력 / 워크플로우 / 산출물)
│   ├── prompts/     ← 각 에이전트·Gate의 시스템 프롬프트
│   ├── gates/       ← Gate 1·2 검증 함수
│   └── llm/         ← Solar API 호출 래퍼
├── inputs/          ← 사용자 입력 JSON
├── outputs/         ← 실행 결과 산출물
├── docs/            ← 기획서 원안
└── pyproject.toml
```

## 기획 문서

상세 기획서는 [`docs/기획서_원안.md`](docs/기획서_원안.md) 참고.

## 라이선스

MIT
