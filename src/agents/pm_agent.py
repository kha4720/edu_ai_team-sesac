"""PM Agent — 기획문서 4종 + 일부 구현 명세서 작성.

기획서 3.6.4 / 5.3 / 5.4 에 정의된 PM Agent 의 책임 산출물:
- 기획문서: service_brief / mvp_scope / user_flow / qa_plan
- 구현명세: data_schema / state_machine / interface_spec  (Phase 4 에서 추가)

각 산출물 작성 함수는 이름 규약 `write_<artifact_id>(harness_input, **inputs)` 로 통일.
공통 로직 (시스템 프롬프트, 호출, 결과 컨테이너) 은 _call_pm 헬퍼로 분리.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat
from src.prompts.pm_mvp_scope import (
    MVP_SCOPE_INSTRUCTION,
    MVP_SCOPE_OUTPUT_HINT,
)
from src.prompts.pm_qa_plan import (
    QA_PLAN_INSTRUCTION,
    QA_PLAN_OUTPUT_HINT,
)
from src.prompts.pm_service_brief import (
    SERVICE_BRIEF_INSTRUCTION,
    SERVICE_BRIEF_OUTPUT_HINT,
)
from src.prompts.pm_system import build_pm_system_prompt
from src.prompts.pm_user_flow import (
    USER_FLOW_INSTRUCTION,
    USER_FLOW_OUTPUT_HINT,
)
from src.schemas.input_schema import HarnessInput


@dataclass
class ArtifactOutput:
    """단일 산출물 작성 결과."""

    artifact_id: str
    markdown: str


def _call_pm(
    *,
    harness_input: HarnessInput,
    artifact_id: str,
    instruction: str,
    output_hint: str,
    primary_blocks: dict[str, str],
    label: str | None = None,
    max_tokens: int = 1500,
    secondary_blocks: dict[str, str] | None = None,
) -> ArtifactOutput:
    """PM Agent 의 단일 산출물 작성 호출.

    Args:
        harness_input: 사용자 입력 (시스템 프롬프트의 target_user + Global Context 의 사용자 입력 블록).
        artifact_id: 만들고 있는 산출물 식별자 (예: "service_brief").
        instruction: 작업 지시문.
        output_hint: 출력 형식 힌트.
        primary_blocks: [Primary Inputs] 블록 (헌법 + 직전 산출물 등).
        label: 호출 로그 라벨 (없으면 artifact_id 사용).
        max_tokens: 응답 토큰 한도.
        secondary_blocks: [Secondary Inputs] 블록 (선택).
    """
    sys_prompt = build_pm_system_prompt(harness_input.service.target_user)
    ctx = PromptContext(
        global_blocks={"사용자 입력": harness_input.to_global_context()},
        primary_blocks=dict(primary_blocks),
        secondary_blocks=dict(secondary_blocks or {}),
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=instruction,
        output_format_hint=output_hint,
    )
    output = chat(
        system=sys_prompt,
        user=user_msg,
        label=label or f"pm-{artifact_id}",
        max_tokens=max_tokens,
    )
    return ArtifactOutput(artifact_id=artifact_id, markdown=output.strip())


# ============================================================
# 산출물별 작성 함수
# ============================================================


def write_service_brief(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
) -> ArtifactOutput:
    """Service Brief 작성.

    Inputs (기획서 5.3.1):
        Global: harness_input + constitution
        Primary: (없음 — 헌법이 직접 근거)
    """
    return _call_pm(
        harness_input=harness_input,
        artifact_id="service_brief",
        instruction=SERVICE_BRIEF_INSTRUCTION,
        output_hint=SERVICE_BRIEF_OUTPUT_HINT,
        primary_blocks={"헌법 (Constitution)": constitution_md},
        max_tokens=1200,
    )


def write_mvp_scope(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    service_brief_md: str,
) -> ArtifactOutput:
    """MVP Scope 작성.

    Inputs (기획서 5.3.2):
        Global: harness_input + constitution
        Primary: service_brief
    """
    return _call_pm(
        harness_input=harness_input,
        artifact_id="mvp_scope",
        instruction=MVP_SCOPE_INSTRUCTION,
        output_hint=MVP_SCOPE_OUTPUT_HINT,
        primary_blocks={
            "헌법 (Constitution)": constitution_md,
            "Service Brief": service_brief_md,
        },
        max_tokens=1500,
    )


def write_user_flow(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    mvp_scope_md: str,
) -> ArtifactOutput:
    """User Flow 작성.

    Inputs (기획서 5.3.3):
        Global: harness_input + constitution
        Primary: mvp_scope
    """
    return _call_pm(
        harness_input=harness_input,
        artifact_id="user_flow",
        instruction=USER_FLOW_INSTRUCTION,
        output_hint=USER_FLOW_OUTPUT_HINT,
        primary_blocks={
            "헌법 (Constitution)": constitution_md,
            "MVP Scope": mvp_scope_md,
        },
        max_tokens=1500,
    )


def write_qa_plan(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    mvp_scope_md: str,
    user_flow_md: str,
    build_plan_md: str,
) -> ArtifactOutput:
    """QA Plan 작성.

    Inputs (기획서 5.3.5):
        Global: harness_input + constitution
        Primary: mvp_scope, user_flow, build_plan
    """
    return _call_pm(
        harness_input=harness_input,
        artifact_id="qa_plan",
        instruction=QA_PLAN_INSTRUCTION,
        output_hint=QA_PLAN_OUTPUT_HINT,
        primary_blocks={
            "헌법 (Constitution)": constitution_md,
            "MVP Scope": mvp_scope_md,
            "User Flow": user_flow_md,
            "Build Plan": build_plan_md,
        },
        max_tokens=2000,
    )
