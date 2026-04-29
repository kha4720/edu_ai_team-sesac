"""Prompt Agent — Prompt Spec 작성.

기획서 3.6.5 / 5.4 에 정의된 Prompt Agent 의 책임:
- 구현명세: prompt_spec

헌법의 교육 설계 원칙(④⑤⑥⑦)을 LLM 이 실제로 따를 수 있는 프롬프트 언어로 번역한다.

Global Context 는 constitution 만 포함 (harness_input.to_global_context() 제외).
target_user 는 시스템 프롬프트 페르소나 구성에만 활용.
"""

from __future__ import annotations

from src.agents.pm_agent import ArtifactOutput
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat
from src.prompts.pm_prompt_spec import PROMPT_SPEC_INSTRUCTION, PROMPT_SPEC_OUTPUT_HINT
from src.prompts.prompt_agent_system import build_prompt_agent_system
from src.schemas.input_schema import HarnessInput


def write_prompt_spec(
    harness_input: HarnessInput,
    *,
    constitution_md: str,
    data_schema_json: str,
    mvp_scope_md: str,
    user_flow_md: str,
    qa_plan_md: str,
) -> ArtifactOutput:
    """Prompt Spec 작성.

    Inputs (기획서 5.4):
        Global: constitution
        Primary: constitution, data_schema
        Secondary: mvp_scope, user_flow, qa_plan

    harness_input 은 target_user 페르소나 구성에만 사용.
    """
    sys_prompt = build_prompt_agent_system(harness_input.service.target_user)
    ctx = PromptContext(
        global_blocks={"헌법 (Constitution)": constitution_md},
        primary_blocks={
            "헌법 (Constitution)": constitution_md,
            "Data Schema": data_schema_json,
        },
        secondary_blocks={
            "MVP Scope": mvp_scope_md,
            "User Flow": user_flow_md,
            "QA Plan": qa_plan_md,
        },
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=PROMPT_SPEC_INSTRUCTION,
        output_format_hint=PROMPT_SPEC_OUTPUT_HINT,
    )
    output = chat(
        system=sys_prompt,
        user=user_msg,
        label="prompt-agent-prompt_spec",
        max_tokens=2500,
    )
    return ArtifactOutput(artifact_id="prompt_spec", markdown=output.strip())
