# Edu Design Harness

> 교육 서비스 기획자가 아이디어와 실행 제약을 입력하면, 5개의 LLM 에이전트(Orchestrator / Edu / PM / Tech / Prompt)가 협업해 **헌법 1종 + 기획문서 5종 + 구현명세 4종** 을 자동 생성하는 멀티에이전트 하네스.

## 산출 흐름

```
사용자 입력 (서비스 기획 정보 + 실행 제약)
        │
        ▼
[Step 2] Edu Agent  ──▶  constitution.md
        │
   Gate 1 검증
        ▼
[Step 3] PM / Tech ──▶  service_brief.md / mvp_scope.md / user_flow.md
                        build_plan.md / qa_plan.md
        │
   Gate 2 검증
        ▼
[Step 4] PM / Prompt ─▶ data_schema.json / state_machine.md
                        prompt_spec.md / interface_spec.md
        │
   Gate 3 검증
        ▼
       완료
```

## 검증 케이스

기획서 4.1 의 **"중학생 질문력 향상 챗봇"** 을 첫 검증 케이스로 사용 (`inputs/question_coach.json`).

## 기술 스택

- Python 3.11+
- [Upstage Solar API](https://console.upstage.ai/) (OpenAI 호환)
- Pydantic v2 (스키마/검증)
- uv (패키지/가상환경 관리)

## 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. .env 작성
cp .env.example .env
# UPSTAGE_API_KEY 값 입력

# 3. Solar API 연결 확인
uv run python -m src.llm._test_solar
```

## 폴더 구조

```
project/
├── src/
│   ├── agents/      ← Edu / PM / Tech / Prompt / Orchestrator
│   ├── schemas/     ← Pydantic 스키마 (입력 / 워크플로우 / 산출물)
│   ├── prompts/     ← 각 에이전트의 시스템 프롬프트
│   ├── gates/       ← Gate 1·2·3 검증 함수
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
