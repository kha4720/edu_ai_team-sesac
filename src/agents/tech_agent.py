"""Tech Agent — Build Plan 작성 + 기술 검토 의견.

기획서 3.6.5 / 5.3.4 에 정의된 Tech Agent 의 책임.
- Build Plan 작성 (Step 3)
- Gate 1/2/3 의 review memo (Phase 1 단순화로 일부 보류 — _TODO.md 참고)
"""

from __future__ import annotations

from src.agents.pm_agent import ArtifactOutput  # 결과 컨테이너 재사용
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat
from src.prompts.tech_build_plan import (
    BUILD_PLAN_INSTRUCTION,
    BUILD_PLAN_OUTPUT_HINT,
)
from src.prompts.tech_system import build_tech_system_prompt
from src.schemas.input_schema import HarnessInput


def write_build_plan(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    mvp_scope_md: str,
    user_flow_md: str,
) -> ArtifactOutput:
    """Build Plan 작성.

    Inputs (기획서 5.3.4):
        Global: harness_input + constitution
        Primary: mvp_scope, user_flow
    """
    sys_prompt = build_tech_system_prompt(harness_input.service.target_user)
    ctx = PromptContext(
        global_blocks={"사용자 입력": harness_input.to_global_context()},
        primary_blocks={
            "헌법 (Constitution)": constitution_md,
            "MVP Scope": mvp_scope_md,
            "User Flow": user_flow_md,
        },
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=BUILD_PLAN_INSTRUCTION,
        output_format_hint=BUILD_PLAN_OUTPUT_HINT,
    )
    output = chat(
        system=sys_prompt,
        user=user_msg,
        label="tech-build_plan",
        max_tokens=2500,
    )
    return ArtifactOutput(artifact_id="build_plan", markdown=output.strip())
