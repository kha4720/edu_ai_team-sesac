"""Gate 3 — 구현 명세서 4종 검증 (다중 검증자 버전).

기획서 5.4 의 검증 구조:
- Team Lead 가 직접 4항목 판단
  (data_schema_completeness / state_machine_consistency / prompt_spec_coverage / interface_spec_alignment)
- Tech Agent 가 구현 가능성 + MVP 제약 적합성 review
- Edu Agent 가 헌법 정합성 + 학습 로직 반영 review
- 세 검증자 결과를 OR 합산 (Gate 1/2 와 동일 패턴)

PM Agent 는 구현 명세서 4종 중 3종(data_schema / state_machine / interface_spec) 의
직접 작성자이므로 자가 검토는 의미 없음 → Gate 3 에는 PM review 미포함.
(같은 원칙으로 Gate 1 에선 Edu 를 제외 — worklog 15 참조)

병렬 실행: Team Lead + Tech + Edu 셋이 서로 독립이므로 ThreadPoolExecutor 로 동시 실행.
재시도/조건부 통과 분기는 LangGraph conditional_edges 가 책임.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.edu_agent import review_spec_4_for_gate3 as edu_review_gate3
from src.agents.tech_agent import review_spec_4_for_gate3 as tech_review_gate3
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat_json
from src.prompts.teamlead_gate3 import GATE3_INSTRUCTION, TEAMLEAD_GATE3_SYSTEM
from src.schemas.input_schema import HarnessInput
from src.schemas.workflow_state import GateResult


class GateCheck(BaseModel):
    ok: bool
    issue: str = ""


class Gate3TeamLeadVerdict(BaseModel):
    """Team Lead 의 직접 검증 4항목 응답."""

    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


@dataclass
class Gate3RoundResult:
    """1회의 검증 라운드 결과 (Team Lead + Tech review + Edu review 모두 포함)."""

    team_lead: Gate3TeamLeadVerdict
    tech_review: dict[str, Any]
    edu_review: dict[str, Any]
    final_verdict: Literal["pass", "fail"]
    aggregated_feedback: str

    def issues_only(self) -> list[str]:
        out: list[str] = []
        for name, ck in self.team_lead.checks.items():
            if not ck.ok:
                out.append(f"Team Lead/{name}: {ck.issue}")
        for name in ("implementation_buildability", "mvp_constraint_fit"):
            ck = self.tech_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"Tech/{name}: {ck.get('issue', '')}")
        for name in ("constitution_alignment", "learning_logic_fit"):
            ck = self.edu_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"Edu/{name}: {ck.get('issue', '')}")
        return out


@dataclass
class Gate3Result:
    final_verdict: GateResult
    round_result: Gate3RoundResult
    risk_memo: str = ""

    # 기존 호출자 호환 (graph.py 의 issues_only 등)
    @property
    def team_lead_verdict(self) -> Gate3TeamLeadVerdict:
        return self.round_result.team_lead

    def issues_only(self) -> list[str]:
        return self.round_result.issues_only()

    def to_log_markdown(self) -> str:
        rd = self.round_result
        lines = [f"## Gate 3 결과: **{self.final_verdict.value}**", ""]
        lines.append("**Team Lead 직접 검증:**")
        for name, ck in rd.team_lead.checks.items():
            mark = "✅" if ck.ok else "❌"
            lines.append(f"- {mark} {name}: {ck.issue or '(통과)'}")
        lines.append("")
        lines.append("**Tech Agent review:**")
        for name in ("implementation_buildability", "mvp_constraint_fit"):
            ck = rd.tech_review.get(name) or {}
            mark = "✅" if ck.get("ok", True) else "❌"
            lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
        if rd.tech_review.get("summary"):
            lines.append(f"- summary: {rd.tech_review['summary']}")
        lines.append("")
        lines.append("**Edu Agent review:**")
        for name in ("constitution_alignment", "learning_logic_fit"):
            ck = rd.edu_review.get(name) or {}
            mark = "✅" if ck.get("ok", True) else "❌"
            lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
        if rd.edu_review.get("summary"):
            lines.append(f"- summary: {rd.edu_review['summary']}")
        if rd.aggregated_feedback:
            lines.append("")
            lines.append(f"**aggregated_feedback:** {rd.aggregated_feedback}")
        if self.risk_memo:
            lines.append("")
            lines.append(f"**risk_memo:** {self.risk_memo}")
        return "\n".join(lines)


# === 핵심 함수 ===


def _team_lead_judge(
    constitution_md: str,
    impl_specs: dict[str, str],
) -> Gate3TeamLeadVerdict:
    ctx = PromptContext(
        global_blocks={"헌법 (Constitution)": constitution_md},
        primary_blocks=impl_specs,
    )
    user_msg = build_user_prompt(context=ctx, instruction=GATE3_INSTRUCTION)
    raw = chat_json(
        system=TEAMLEAD_GATE3_SYSTEM,
        user=user_msg,
        label="gate3-team_lead",
        max_tokens=2500,
    )
    checks = raw.get("checks") or {}
    raw["checks"] = {k: v for k, v in checks.items() if isinstance(v, dict)}
    if "feedback_memo" in checks and isinstance(checks["feedback_memo"], str) and not raw.get("feedback_memo"):
        raw["feedback_memo"] = checks["feedback_memo"]
    return Gate3TeamLeadVerdict.model_validate(raw)


def _aggregate_round(
    team_lead: Gate3TeamLeadVerdict,
    tech: dict[str, Any],
    edu: dict[str, Any],
) -> Gate3RoundResult:
    """3 검증자 결과 OR 합산. (Gate 1/2 와 동일 패턴)"""
    issues: list[str] = []

    for name, ck in team_lead.checks.items():
        if not ck.ok:
            issues.append(f"[Team Lead/{name}] {ck.issue}")
    for name in ("implementation_buildability", "mvp_constraint_fit"):
        ck = tech.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[Tech/{name}] {ck.get('issue', '')}")
    for name in ("constitution_alignment", "learning_logic_fit"):
        ck = edu.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[Edu/{name}] {ck.get('issue', '')}")

    final = "pass" if not issues else "fail"
    aggregated = (
        team_lead.feedback_memo if final == "fail" and team_lead.feedback_memo else ""
    )
    if issues:
        aggregated = (
            (team_lead.feedback_memo + "\n\n" if team_lead.feedback_memo else "")
            + "추가 검토 의견:\n- "
            + "\n- ".join(issues)
        )

    return Gate3RoundResult(
        team_lead=team_lead,
        tech_review=tech,
        edu_review=edu,
        final_verdict=final,
        aggregated_feedback=aggregated,
    )


def run_gate3(
    harness_input: HarnessInput,
    constitution_md: str,
    impl_specs: dict[str, str],
) -> Gate3Result:
    """구현 명세서 4종 검증 1회 수행 (재시도 없음).

    재시도/조건부 통과 분기는 LangGraph conditional_edges 가 책임.
    """
    print("[Gate 3] Team Lead + Tech + Edu 병렬 검증 시작")
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_orch = pool.submit(_team_lead_judge, constitution_md, impl_specs)
        f_tech = pool.submit(tech_review_gate3, harness_input, constitution_md, impl_specs)
        f_edu = pool.submit(edu_review_gate3, harness_input, constitution_md, impl_specs)
        orch = f_orch.result()
        tech = f_tech.result()
        edu = f_edu.result()

    round_result = _aggregate_round(orch, tech, edu)
    final = (
        GateResult.PASS_ if round_result.final_verdict == "pass" else GateResult.FAIL
    )
    return Gate3Result(final_verdict=final, round_result=round_result)
