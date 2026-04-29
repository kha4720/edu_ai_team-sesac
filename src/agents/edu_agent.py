"""Edu Agent — 헌법(Constitution) 생성 책임.

기획서 3.6.3(Edu Agent) / 5.2.3 / 5.2.4 에 정의된 헌법 작성 절차를 코드로 구현한다.

호출 전략 (Phase 2-3 결정):
- ①~③ "설계 근거" 3단계는 한 번의 호출로 묶어서 받는다 (묶음 호출).
- ④~⑦ "헌법 본체" 4단계는 각각 분리 호출 (후속 9종 문서가 직접 참조하므로 형식 강제).
- 총 5번 호출.
- ①~③ 응답은 헤더 기준으로 3섹션 분리해 ④~⑦ 단계의 [Primary Inputs] 에 개별 블록으로 넣는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat, chat_json
from src.prompts.edu_constitution import (
    STAGE1TO3_INSTRUCTION,
    STAGE1TO3_OUTPUT_HINT,
    STAGE4_INSTRUCTION,
    STAGE4_OUTPUT_HINT,
    STAGE5_INSTRUCTION,
    STAGE5_OUTPUT_HINT,
    STAGE6_INSTRUCTION,
    STAGE6_OUTPUT_HINT,
    STAGE7_INSTRUCTION,
    STAGE7_OUTPUT_HINT,
)
from src.prompts.edu_review import (
    EDU_REVIEW_GATE2_INSTRUCTION,
    EDU_REVIEW_GATE3_INSTRUCTION,
)
from src.prompts.edu_system import (
    build_edu_constitution_write_overlay,
    build_edu_persona_prompt,
    build_edu_review_overlay,
    compose_edu_system_prompt,
)
from src.schemas.input_schema import HarnessInput

# ④~⑦ 분리 호출용 정의 (라벨 / 결과 키 / 지시문 / max_tokens / 출력 힌트)
_LATE_STAGES: list[tuple[str, str, str, int, str]] = [
    ("c-stage4", "헌법 ④ 결과", STAGE4_INSTRUCTION, 700, STAGE4_OUTPUT_HINT),
    ("c-stage5", "헌법 ⑤ 결과", STAGE5_INSTRUCTION, 500, STAGE5_OUTPUT_HINT),
    ("c-stage6", "헌법 ⑥ 결과", STAGE6_INSTRUCTION, 1200, STAGE6_OUTPUT_HINT),
    ("c-stage7", "헌법 ⑦ 결과", STAGE7_INSTRUCTION, 1500, STAGE7_OUTPUT_HINT),
]

# ①~③ 묶음 응답에서 3섹션을 분리할 때 쓰는 헤더 패턴
_STAGE_HEADERS = {
    "헌법 ① 결과": "## ① 교육공학적 문제 재정의",
    "헌법 ② 결과": "## ② 교수 기법 탐색",
    "헌법 ③ 결과": "## ③ MVP 교수 기법 선정",
}


@dataclass
class ConstitutionResult:
    """헌법 작성 결과를 담는 컨테이너."""

    markdown: str
    stage_outputs: dict[str, str] = field(default_factory=dict)


def _split_stage1to3(combined: str) -> dict[str, str]:
    """①~③ 묶음 응답을 헤더 기준으로 3섹션 분리해 dict 로 반환.

    헤더가 누락되면 전체 응답을 ① 결과로 두고 ②③ 은 빈 문자열로 둔다 (Gate 1 에서 fail 처리될 것).
    """
    headers = list(_STAGE_HEADERS.values())
    # 각 헤더의 시작 인덱스 찾기
    positions: list[tuple[str, int]] = []
    for h in headers:
        m = re.search(re.escape(h), combined)
        if m:
            positions.append((h, m.start()))

    if len(positions) != 3:
        # 분리 실패 — 전체 응답을 ① 결과로 보존하고 ②③ 빈 문자열
        return {
            "헌법 ① 결과": combined.strip(),
            "헌법 ② 결과": "",
            "헌법 ③ 결과": "",
        }

    # 시작 인덱스 순으로 정렬한 뒤 다음 헤더 시작 직전까지를 한 섹션으로
    positions.sort(key=lambda x: x[1])
    sections: dict[str, str] = {}
    for i, (h, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(combined)
        # 헤더 → 결과 키 매핑
        key = next(k for k, v in _STAGE_HEADERS.items() if v == h)
        sections[key] = combined[start:end].strip()
    return sections


def _assemble_markdown(stage_outputs: dict[str, str]) -> str:
    """7개 단계 산출을 기획서 5.2.8 의 기본 목차 구조에 맞춰 합친다."""
    return (
        "# Constitution\n\n"
        "## A. 설계 근거\n\n"
        f"{stage_outputs['헌법 ① 결과']}\n\n"
        f"{stage_outputs['헌법 ② 결과']}\n\n"
        f"{stage_outputs['헌법 ③ 결과']}\n\n"
        "## B. 실행 기준\n\n"
        f"{stage_outputs['헌법 ④ 결과']}\n\n"
        f"{stage_outputs['헌법 ⑤ 결과']}\n\n"
        f"{stage_outputs['헌법 ⑥ 결과']}\n\n"
        f"{stage_outputs['헌법 ⑦ 결과']}\n"
    )


def write_constitution(harness_input: HarnessInput) -> ConstitutionResult:
    """헌법을 5번 호출(①~③ 묶음 + ④⑤⑥⑦ 분리)로 작성하고 합쳐진 마크다운을 반환한다."""
    persona_prompt = build_edu_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_edu_system_prompt(
        persona_prompt,
        build_edu_constitution_write_overlay(),
    )
    global_blocks = {"사용자 입력": harness_input.to_global_context()}

    stage_outputs: dict[str, str] = {}

    # === 1번 호출: ①~③ 묶음 ===
    ctx = PromptContext(global_blocks=global_blocks)
    user_msg = build_user_prompt(
        context=ctx,
        instruction=STAGE1TO3_INSTRUCTION,
        output_format_hint=STAGE1TO3_OUTPUT_HINT,
    )
    combined = chat(
        system=sys_prompt,
        user=user_msg,
        label="c-stage1to3",
        max_tokens=2000,
    )
    stage_outputs.update(_split_stage1to3(combined))

    # === ④~⑦ 분리 호출 ===
    for label, key, instruction, max_tokens, hint in _LATE_STAGES:
        ctx = PromptContext(
            global_blocks=global_blocks,
            primary_blocks=dict(stage_outputs),  # 누적 주입
        )
        user_msg = build_user_prompt(
            context=ctx,
            instruction=instruction,
            output_format_hint=hint,
        )
        output = chat(
            system=sys_prompt,
            user=user_msg,
            label=label,
            max_tokens=max_tokens,
        )
        stage_outputs[key] = output.strip()

    markdown = _assemble_markdown(stage_outputs)
    return ConstitutionResult(markdown=markdown, stage_outputs=stage_outputs)


# ============================================================
# Review (Gate 의 의견 수합용)
# ============================================================


def review_planning_5_for_gate2(
    harness_input: HarnessInput,
    constitution_md: str,
    artifact_blocks: dict[str, str],
) -> dict[str, Any]:
    """Gate 2 에서 Orchestrator 가 호출하는 Edu Agent review.

    Returns:
        JSON dict — constitution_alignment / learning_effectiveness / summary
    """
    persona_prompt = build_edu_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_edu_system_prompt(
        persona_prompt,
        build_edu_review_overlay(),
    )
    ctx = PromptContext(
        global_blocks={
            "사용자 입력": harness_input.to_global_context(),
            "헌법 (Constitution)": constitution_md,
        },
        primary_blocks=dict(artifact_blocks),
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=EDU_REVIEW_GATE2_INSTRUCTION,
    )
    return chat_json(
        system=sys_prompt,
        user=user_msg,
        label="edu-review-gate2",
        max_tokens=1500,
    )


def review_spec_4_for_gate3(
    harness_input: HarnessInput,
    constitution_md: str,
    impl_spec_blocks: dict[str, str],
) -> dict[str, Any]:
    """Gate 3 에서 Orchestrator 가 호출하는 Edu Agent review.

    Returns:
        JSON dict — constitution_alignment / learning_logic_fit / summary
    """
    persona_prompt = build_edu_persona_prompt(harness_input.service.target_user)
    sys_prompt = compose_edu_system_prompt(
        persona_prompt,
        build_edu_review_overlay(),
    )
    ctx = PromptContext(
        global_blocks={"헌법 (Constitution)": constitution_md},
        primary_blocks=dict(impl_spec_blocks),
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=EDU_REVIEW_GATE3_INSTRUCTION,
    )
    return chat_json(
        system=sys_prompt,
        user=user_msg,
        label="edu-review-gate3",
        max_tokens=1500,
    )
