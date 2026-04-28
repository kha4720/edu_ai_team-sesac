"""Gate 2 — 기획문서 5종 검증 (다중 검증자 버전).

기획서 5.3.6 의 검증 구조 그대로:
- Orchestrator 가 직접 5항목 판단
- Edu Agent 가 헌법 정합성 + 학습 효과성 review
- Tech Agent 가 기술 실행 가능성 + 구현 계획 타당성 review
- Orchestrator 가 자기 판단 + 두 review 를 종합해 최종 verdict

fail 시 feedback_memo 를 받아 5종 모두 재작성 → 재검증 (1회까지).
재시도 후에도 fail 이면 conditional_pass + risk_memo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.edu_agent import review_planning_5_for_gate2 as edu_review_gate2
from src.agents.pm_agent import (
    ArtifactOutput,
    write_mvp_scope,
    write_qa_plan,
    write_service_brief,
    write_user_flow,
)
from src.agents.tech_agent import (
    review_planning_5_for_gate2 as tech_review_gate2,
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


class Gate2OrchestratorVerdict(BaseModel):
    """Orchestrator 의 직접 검증 5항목 응답."""

    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


@dataclass
class Gate2RoundResult:
    """1회의 검증 라운드 결과 (Orchestrator + Edu review + Tech review 모두 포함)."""

    orchestrator: Gate2OrchestratorVerdict
    edu_review: dict[str, Any]
    tech_review: dict[str, Any]
    final_verdict: Literal["pass", "fail"]
    aggregated_feedback: str

    def issues_only(self) -> list[str]:
        """ok=false 인 항목들의 issue 텍스트만 추림."""
        out: list[str] = []
        for name, ck in self.orchestrator.checks.items():
            if not ck.ok:
                out.append(f"Orchestrator/{name}: {ck.issue}")
        for name in ("constitution_alignment", "learning_effectiveness"):
            ck = self.edu_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"Edu/{name}: {ck.get('issue', '')}")
        for name in ("technical_feasibility", "build_plan_validity"):
            ck = self.tech_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"Tech/{name}: {ck.get('issue', '')}")
        return out


@dataclass
class PlanningArtifacts:
    """기획문서 5종 한 묶음."""

    service_brief: ArtifactOutput
    mvp_scope: ArtifactOutput
    user_flow: ArtifactOutput
    build_plan: ArtifactOutput
    qa_plan: ArtifactOutput

    def as_blocks(self) -> dict[str, str]:
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
    rounds: list[Gate2RoundResult] = field(default_factory=list)
    risk_memo: str = ""

    def to_log_markdown(self) -> str:
        lines = [f"## Gate 2 결과: **{self.final_verdict.value}**", ""]
        for i, rd in enumerate(self.rounds, start=1):
            lines.append(f"### 시도 {i} — 종합 verdict: {rd.final_verdict}")
            # Orchestrator
            lines.append("")
            lines.append("**Orchestrator 직접 검증:**")
            for name, ck in rd.orchestrator.checks.items():
                mark = "✅" if ck.ok else "❌"
                lines.append(f"- {mark} {name}: {ck.issue or '(통과)'}")
            # Edu
            lines.append("")
            lines.append("**Edu Agent review:**")
            for name in ("constitution_alignment", "learning_effectiveness"):
                ck = rd.edu_review.get(name) or {}
                mark = "✅" if ck.get("ok", True) else "❌"
                lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
            if rd.edu_review.get("summary"):
                lines.append(f"- summary: {rd.edu_review['summary']}")
            # Tech
            lines.append("")
            lines.append("**Tech Agent review:**")
            for name in ("technical_feasibility", "build_plan_validity"):
                ck = rd.tech_review.get(name) or {}
                mark = "✅" if ck.get("ok", True) else "❌"
                lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
            if rd.tech_review.get("summary"):
                lines.append(f"- summary: {rd.tech_review['summary']}")

            if rd.aggregated_feedback:
                lines.append("")
                lines.append(f"**aggregated_feedback:** {rd.aggregated_feedback}")
            lines.append("")
        if self.risk_memo:
            lines.append(f"**risk_memo:** {self.risk_memo}")
        return "\n".join(lines)


# === 핵심 함수 ===


def _orchestrator_judge(
    harness_input: HarnessInput,
    constitution_md: str,
    artifacts: PlanningArtifacts,
) -> Gate2OrchestratorVerdict:
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
        label="gate2-orchestrator",
        max_tokens=2000,
    )
    # 안전망: LLM 이 가끔 feedback_memo 같은 비-GateCheck 값을 checks 안에 넣음.
    # dict 가 아닌 값은 위로 끌어올리거나 무시한다.
    checks = raw.get("checks") or {}
    raw["checks"] = {k: v for k, v in checks.items() if isinstance(v, dict)}
    if "feedback_memo" in checks and isinstance(checks["feedback_memo"], str) and not raw.get("feedback_memo"):
        raw["feedback_memo"] = checks["feedback_memo"]
    return Gate2OrchestratorVerdict.model_validate(raw)


def _aggregate_round(
    orchestrator: Gate2OrchestratorVerdict,
    edu: dict[str, Any],
    tech: dict[str, Any],
) -> Gate2RoundResult:
    """3 검증자 결과를 종합해 최종 verdict 와 feedback 을 만든다.

    종합 규칙 (단순):
        - 누구라도 ok=false 가 있으면 final_verdict = fail
        - 모두 ok=true 이면 final_verdict = pass
        - feedback 은 모든 fail 항목의 issue 를 모은 텍스트
    """
    issues: list[str] = []

    # Orchestrator
    for name, ck in orchestrator.checks.items():
        if not ck.ok:
            issues.append(f"[Orchestrator/{name}] {ck.issue}")
    # Edu
    for name in ("constitution_alignment", "learning_effectiveness"):
        ck = edu.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[Edu/{name}] {ck.get('issue', '')}")
    # Tech
    for name in ("technical_feasibility", "build_plan_validity"):
        ck = tech.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[Tech/{name}] {ck.get('issue', '')}")

    final = "pass" if not issues else "fail"
    aggregated = (
        orchestrator.feedback_memo if final == "fail" and orchestrator.feedback_memo else ""
    )
    if issues:
        aggregated = (
            (orchestrator.feedback_memo + "\n\n" if orchestrator.feedback_memo else "")
            + "추가 검토 의견:\n- "
            + "\n- ".join(issues)
        )

    return Gate2RoundResult(
        orchestrator=orchestrator,
        edu_review=edu,
        tech_review=tech,
        final_verdict=final,
        aggregated_feedback=aggregated,
    )


def _judge_round(
    harness_input: HarnessInput,
    constitution_md: str,
    artifacts: PlanningArtifacts,
) -> Gate2RoundResult:
    print("[Gate 2] Orchestrator 직접 검증")
    orch = _orchestrator_judge(harness_input, constitution_md, artifacts)
    print("[Gate 2] Edu Agent review")
    edu = edu_review_gate2(harness_input, constitution_md, artifacts.as_blocks())
    print("[Gate 2] Tech Agent review")
    tech = tech_review_gate2(harness_input, constitution_md, artifacts.as_blocks())
    return _aggregate_round(orch, edu, tech)


def _rewrite_planning_5(
    harness_input: HarnessInput,
    constitution_md: str,
) -> PlanningArtifacts:
    """5종 모두 재호출. MVP 단순화."""
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
    """기획문서 5종 검증 (다중 검증자) + 재시도까지 처리."""
    rounds: list[Gate2RoundResult] = []
    current = artifacts

    print("[Gate 2] 1차 검증 시작 (Orchestrator + Edu + Tech)")
    r1 = _judge_round(harness_input, constitution_md, current)
    rounds.append(r1)
    if r1.final_verdict == "pass":
        return Gate2Result(final_verdict=GateResult.PASS_, artifacts=current, rounds=rounds)

    if max_retries < 1:
        return Gate2Result(final_verdict=GateResult.FAIL, artifacts=current, rounds=rounds)

    print(f"[Gate 2] FAIL → 5종 재작성 (feedback: {r1.aggregated_feedback[:100]}...)")
    current = _rewrite_planning_5(harness_input, constitution_md)

    print("[Gate 2] 2차 검증 시작")
    r2 = _judge_round(harness_input, constitution_md, current)
    rounds.append(r2)
    if r2.final_verdict == "pass":
        return Gate2Result(final_verdict=GateResult.PASS_, artifacts=current, rounds=rounds)

    risk = "Gate 2 동일 검증 항목 2회 연속 미흡. 잔존 issue: " + " | ".join(r2.issues_only())
    return Gate2Result(
        final_verdict=GateResult.CONDITIONAL_PASS,
        artifacts=current,
        rounds=rounds,
        risk_memo=risk,
    )