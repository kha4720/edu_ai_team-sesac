"""Gate 2 — 기획문서 5종(Service Brief / MVP Scope / User Flow / Build Plan / QA Plan) 검증.

기획서 5.3.6 의 검증 항목을 Orchestrator 가 LLM-as-judge 방식으로 직접 판단.
fail 시 feedback_memo 를 받아 5종 모두 재작성 → 재검증 (1회까지).
재시도 후에도 fail 이면 conditional_pass + risk_memo.

재작성 전략 (MVP 단순화):
- 어느 문서가 문제인지에 따라 부분 재호출이 이상적이지만, 의존성 사슬 때문에 까다로움.
- 일단 5종 전부 다시 작성. 정교한 부분 재호출은 _TODO.md 우선순위 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from src.agents.pm_agent import (
    ArtifactOutput,
    write_mvp_scope,
    write_qa_plan,
    write_service_brief,
    write_user_flow,
)
from src.agents.tech_agent import write_build_plan
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat_json
from src.prompts.orchestrator_gate2 import (
    GATE2_INSTRUCTION,
    ORCHESTRATOR_GATE2_SYSTEM,
)
from src.schemas.input_schema import HarnessInput
from src.schemas.workflow_state import GateResult


class GateCheck(BaseModel):
    ok: bool
    issue: str = ""


class Gate2Verdict(BaseModel):
    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


@dataclass
class PlanningArtifacts:
    """기획문서 5종 한 묶음."""

    service_brief: ArtifactOutput
    mvp_scope: ArtifactOutput
    user_flow: ArtifactOutput
    build_plan: ArtifactOutput
    qa_plan: ArtifactOutput

    def as_blocks(self) -> dict[str, str]:
        """Gate 검증 시 user 메시지의 [Primary Inputs] 블록으로 넣을 dict 형태."""
        return {
            "Service Brief": self.service_brief.markdown,
            "MVP Scope": self.mvp_scope.markdown,
            "User Flow": self.user_flow.markdown,
            "Build Plan": self.build_plan.markdown,
            "QA Plan": self.qa_plan.markdown,
        }


@dataclass
class Gate2Result:
    final_verdict: GateResult
    artifacts: PlanningArtifacts
    attempts: list[Gate2Verdict] = field(default_factory=list)
    risk_memo: str = ""

    def to_log_markdown(self) -> str:
        lines = [f"## Gate 2 결과: **{self.final_verdict.value}**", ""]
        for i, att in enumerate(self.attempts, start=1):
            lines.append(f"### 시도 {i} — verdict: {att.verdict}")
            for name, ck in att.checks.items():
                mark = "✅" if ck.ok else "❌"
                lines.append(f"- {mark} **{name}**: {ck.issue or '(통과)'}")
            if att.feedback_memo:
                lines.append("")
                lines.append(f"**feedback_memo:** {att.feedback_memo}")
            lines.append("")
        if self.risk_memo:
            lines.append(f"**risk_memo:** {self.risk_memo}")
        return "\n".join(lines)


def _judge_once(
    harness_input: HarnessInput,
    constitution_md: str,
    artifacts: PlanningArtifacts,
) -> Gate2Verdict:
    ctx = PromptContext(
        global_blocks={
            "사용자 입력": harness_input.to_global_context(),
            "헌법 (Constitution)": constitution_md,
        },
        primary_blocks=artifacts.as_blocks(),
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=GATE2_INSTRUCTION,
    )
    raw = chat_json(
        system=ORCHESTRATOR_GATE2_SYSTEM,
        user=user_msg,
        label="gate2-judge",
        max_tokens=2000,
    )
    return Gate2Verdict.model_validate(raw)


def _rewrite_planning_5(
    harness_input: HarnessInput,
    constitution_md: str,
) -> PlanningArtifacts:
    """5종 모두 재호출. MVP 단순화 — 부분 재호출은 _TODO.md 참고."""
    sb = write_service_brief(harness_input, constitution_md=constitution_md)
    ms = write_mvp_scope(harness_input, constitution_md=constitution_md, service_brief_md=sb.markdown)
    uf = write_user_flow(harness_input, constitution_md=constitution_md, mvp_scope_md=ms.markdown)
    bp = write_build_plan(harness_input, constitution_md=constitution_md, mvp_scope_md=ms.markdown, user_flow_md=uf.markdown)
    qa = write_qa_plan(harness_input, constitution_md=constitution_md, mvp_scope_md=ms.markdown, user_flow_md=uf.markdown, build_plan_md=bp.markdown)
    return PlanningArtifacts(
        service_brief=sb, mvp_scope=ms, user_flow=uf, build_plan=bp, qa_plan=qa,
    )


def run_gate2(
    harness_input: HarnessInput,
    constitution_md: str,
    artifacts: PlanningArtifacts,
    *,
    max_retries: int = 1,
) -> Gate2Result:
    """기획문서 5종 검증 + 재시도까지 처리한다."""
    attempts: list[Gate2Verdict] = []
    current = artifacts

    print("[Gate 2] 1차 검증 시작")
    verdict1 = _judge_once(harness_input, constitution_md, current)
    attempts.append(verdict1)
    if verdict1.verdict == "pass":
        return Gate2Result(final_verdict=GateResult.PASS_, artifacts=current, attempts=attempts)

    if max_retries < 1:
        return Gate2Result(final_verdict=GateResult.FAIL, artifacts=current, attempts=attempts)

    print(f"[Gate 2] FAIL → 5종 재작성 (feedback: {verdict1.feedback_memo[:80]}...)")
    current = _rewrite_planning_5(harness_input, constitution_md)

    print("[Gate 2] 2차 검증 시작")
    verdict2 = _judge_once(harness_input, constitution_md, current)
    attempts.append(verdict2)
    if verdict2.verdict == "pass":
        return Gate2Result(final_verdict=GateResult.PASS_, artifacts=current, attempts=attempts)

    risk = (
        "Gate 2 동일 검증 항목 2회 연속 미흡. "
        "잔존 issue: "
        + "; ".join(
            f"{name}: {ck.issue}" for name, ck in verdict2.checks.items() if not ck.ok
        )
    )
    return Gate2Result(
        final_verdict=GateResult.CONDITIONAL_PASS,
        artifacts=current,
        attempts=attempts,
        risk_memo=risk,
    )