"""PM Agent — 기획문서 4종 + 일부 구현 명세서 작성 + Gate review.

기획서 3.6.4 / 5.3 / 5.4 에 정의된 PM Agent 의 책임 산출물:
- 기획문서: service_brief / mvp_scope / user_flow / qa_plan
- 구현명세: data_schema / state_machine / interface_spec  (Phase 4 에서 추가)

Review:
- Gate 1: 헌법의 기획 활용성 검토

각 산출물 작성 함수는 이름 규약 `write_<artifact_id>(harness_input, **inputs)` 로 통일.
공통 로직 (시스템 프롬프트, 호출, 결과 컨테이너) 은 _call_pm 헬퍼로 분리.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat, chat_json
from src.prompts.pm_data_schema import DATA_SCHEMA_INSTRUCTION, DATA_SCHEMA_OUTPUT_HINT
from src.prompts.pm_interface_spec import (
    INTERFACE_SPEC_INSTRUCTION,
    INTERFACE_SPEC_OUTPUT_HINT,
)
from src.prompts.pm_mvp_scope import (
    MVP_SCOPE_INSTRUCTION,
    MVP_SCOPE_OUTPUT_HINT,
)
from src.prompts.pm_qa_plan import (
    QA_PLAN_INSTRUCTION,
    QA_PLAN_OUTPUT_HINT,
)
from src.prompts.pm_review import (
    PM_REVIEW_GATE1_INSTRUCTION,
)
from src.prompts.pm_service_brief import (
    SERVICE_BRIEF_INSTRUCTION,
    SERVICE_BRIEF_OUTPUT_HINT,
)
from src.prompts.pm_state_machine import (
    STATE_MACHINE_INSTRUCTION,
    STATE_MACHINE_OUTPUT_HINT,
)
from src.prompts.pm_system import (
    build_pm_persona_prompt,
    build_pm_review_overlay,
    build_pm_write_overlay,
    compose_pm_system_prompt,
)
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
    persona_prompt = build_pm_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_pm_system_prompt(
        persona_prompt,
        build_pm_write_overlay(),
    )
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


# ============================================================
# Step 4 헬퍼 — Global Context 는 constitution 만 (harness_input 제외)
# ============================================================


def _call_pm_step4(
    *,
    harness_input: HarnessInput,
    constitution_md: str,
    artifact_id: str,
    instruction: str,
    output_hint: str,
    primary_blocks: dict[str, str],
    secondary_blocks: dict[str, str] | None = None,
    label: str | None = None,
    max_tokens: int = 1500,
) -> ArtifactOutput:
    """Step 4 전용 PM 호출 헬퍼.

    _call_pm 과 달리 global_blocks 에 harness_input.to_global_context() 를 넣지 않는다.
    실행 제약은 Gate 2 통과 시 기획 5종에 이미 반영됐으므로 불필요.
    target_user 는 시스템 프롬프트 페르소나 구성에만 활용.
    """
    persona_prompt = build_pm_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_pm_system_prompt(persona_prompt, build_pm_write_overlay())
    ctx = PromptContext(
        global_blocks={"헌법 (Constitution)": constitution_md},
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
# Step 4 산출물 작성 함수
# ============================================================


def write_data_schema(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    mvp_scope_md: str,
    user_flow_md: str,
    build_plan_md: str,
) -> ArtifactOutput:
    """Data Schema 작성.

    Inputs (기획서 5.4):
        Global: constitution
        Primary: mvp_scope, user_flow
        Secondary: build_plan
    """
    return _call_pm_step4(
        harness_input=harness_input,
        constitution_md=constitution_md,
        artifact_id="data_schema",
        instruction=DATA_SCHEMA_INSTRUCTION,
        output_hint=DATA_SCHEMA_OUTPUT_HINT,
        primary_blocks={
            "MVP Scope": mvp_scope_md,
            "User Flow": user_flow_md,
        },
        secondary_blocks={"Build Plan": build_plan_md},
        max_tokens=1500,
    )


def write_state_machine(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    user_flow_md: str,
    qa_plan_md: str,
    build_plan_md: str,
    mvp_scope_md: str,
    data_schema_json: str,
) -> ArtifactOutput:
    """State Machine 작성.

    Inputs (기획서 5.4):
        Global: constitution
        Primary: user_flow, qa_plan
        Secondary: build_plan, mvp_scope, data_schema
    """
    return _call_pm_step4(
        harness_input=harness_input,
        constitution_md=constitution_md,
        artifact_id="state_machine",
        instruction=STATE_MACHINE_INSTRUCTION,
        output_hint=STATE_MACHINE_OUTPUT_HINT,
        primary_blocks={
            "User Flow": user_flow_md,
            "QA Plan": qa_plan_md,
        },
        secondary_blocks={
            "Build Plan": build_plan_md,
            "MVP Scope": mvp_scope_md,
            "Data Schema": data_schema_json,
        },
        max_tokens=2000,
    )


def write_interface_spec(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    user_flow_md: str,
    data_schema_json: str,
    build_plan_md: str,
    state_machine_md: str,
) -> ArtifactOutput:
    """Interface Spec 작성.

    Inputs (기획서 5.4):
        Global: constitution
        Primary: user_flow, data_schema
        Secondary: build_plan, state_machine
    """
    return _call_pm_step4(
        harness_input=harness_input,
        constitution_md=constitution_md,
        artifact_id="interface_spec",
        instruction=INTERFACE_SPEC_INSTRUCTION,
        output_hint=INTERFACE_SPEC_OUTPUT_HINT,
        primary_blocks={
            "User Flow": user_flow_md,
            "Data Schema": data_schema_json,
        },
        secondary_blocks={
            "Build Plan": build_plan_md,
            "State Machine": state_machine_md,
        },
        max_tokens=2000,
    )


# ============================================================
# Review (Gate 의 의견 수합용)
# ============================================================


def review_constitution_for_gate1(
    harness_input: HarnessInput,
    constitution_md: str,
) -> dict[str, Any]:
    """Gate 1 에서 Team Lead 가 호출하는 PM Agent review.

    Returns:
        JSON dict — planning_usability / mvp_realism / summary
    """
    persona_prompt = build_pm_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_pm_system_prompt(
        persona_prompt,
        build_pm_review_overlay(),
    )
    ctx = PromptContext(
        global_blocks={"사용자 입력": harness_input.to_global_context()},
        primary_blocks={"헌법 (Constitution)": constitution_md},
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=PM_REVIEW_GATE1_INSTRUCTION,
    )
    return chat_json(
        system=sys_prompt,
        user=user_msg,
        label="pm-review-gate1",
        max_tokens=1500,
    )
