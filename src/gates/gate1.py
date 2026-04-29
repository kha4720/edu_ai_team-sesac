"""Gate 1 — 헌법(Constitution) 검증 (다중 검증자 버전).

기획서 5.2.6 의 검증 구조 그대로:
- Team Lead 가 직접 4항목 판단 (completeness / top_consistency / internal_link / evidence_validity)
- PM Agent 가 기획 활용성 + MVP 범위 현실성 review
- Tech Agent 가 헌법 흐름 구현 가능성 + 실행 제약 적합성 review
- Team Lead 가 자기 판단 + 두 review 를 종합해 최종 verdict

설계 결정 (Phase A):
- 함수 내부 retry 로직 제거. 1회 검증만 수행하고 결과 반환.
- 재시도/조건부 통과 분기는 LangGraph conditional_edges (Phase B) 가 책임.
- Edu Agent 는 자기가 작성한 헌법을 자기가 검토하는 게 의미 없으므로 Gate 1 의견 수합 X.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.edu_agent import ConstitutionResult
from src.agents.pm_agent import (
    review_constitution_for_gate1 as pm_review_gate1,
)
from src.agents.tech_agent import (
    review_constitution_for_gate1 as tech_review_gate1,
)
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat_json
from src.prompts.teamlead_gate1 import (
    GATE1_INSTRUCTION,
    TEAMLEAD_GATE1_SYSTEM,
)
from src.schemas.input_schema import HarnessInput
from src.schemas.workflow_state import GateResult


class GateCheck(BaseModel):
    ok: bool
    issue: str = ""


class Gate1TeamLeadVerdict(BaseModel):
    """Team Lead 의 직접 검증 4항목 응답."""

    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


@dataclass
class Gate1RoundResult:
    """1회의 검증 라운드 결과 (Team Lead + PM review + Tech review 모두 포함)."""

    team_lead: Gate1TeamLeadVerdict
    pm_review: dict[str, Any]
    tech_review: dict[str, Any]
    final_verdict: Literal["pass", "fail"]
    aggregated_feedback: str

    def issues_only(self) -> list[str]:
        """ok=false 인 항목들의 issue 텍스트만 추림."""
        out: list[str] = []
        for name, ck in self.team_lead.checks.items():
            if not ck.ok:
                out.append(f"Team Lead/{name}: {ck.issue}")
        for name in ("planning_usability", "mvp_realism"):
            ck = self.pm_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"PM/{name}: {ck.get('issue', '')}")
        for name in ("constitution_buildability", "constraint_fit"):
            ck = self.tech_review.get(name) or {}
            if not ck.get("ok", True):
                out.append(f"Tech/{name}: {ck.get('issue', '')}")
        return out


@dataclass
class Gate1Result:
    """Gate 1 1회 검증 결과 (재시도 없음 — Phase A 부터)."""

    final_verdict: GateResult  # PASS_ / FAIL (CONDITIONAL_PASS 는 그래프가 결정)
    constitution: ConstitutionResult
    round_result: Gate1RoundResult

    def to_log_markdown(self) -> str:
        rd = self.round_result
        lines = [f"## Gate 1 결과: **{self.final_verdict.value}**", ""]
        lines.append("**Team Lead 직접 검증:**")
        for name, ck in rd.team_lead.checks.items():
            mark = "✅" if ck.ok else "❌"
            lines.append(f"- {mark} {name}: {ck.issue or '(통과)'}")
        lines.append("")
        lines.append("**PM Agent review:**")
        for name in ("planning_usability", "mvp_realism"):
            ck = rd.pm_review.get(name) or {}
            mark = "✅" if ck.get("ok", True) else "❌"
            lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
        if rd.pm_review.get("summary"):
            lines.append(f"- summary: {rd.pm_review['summary']}")
        lines.append("")
        lines.append("**Tech Agent review:**")
        for name in ("constitution_buildability", "constraint_fit"):
            ck = rd.tech_review.get(name) or {}
            mark = "✅" if ck.get("ok", True) else "❌"
            lines.append(f"- {mark} {name}: {ck.get('issue') or '(통과)'}")
        if rd.tech_review.get("summary"):
            lines.append(f"- summary: {rd.tech_review['summary']}")
        if rd.aggregated_feedback:
            lines.append("")
            lines.append(f"**aggregated_feedback:** {rd.aggregated_feedback}")
        return "\n".join(lines)


# === 핵심 함수 ===


def _team_lead_judge(
    harness_input: HarnessInput, constitution_md: str
) -> Gate1TeamLeadVerdict:
    ctx = PromptContext(
        global_blocks={"사용자 입력": harness_input.to_global_context()},
        primary_blocks={"검증 대상 헌법": constitution_md},
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=GATE1_INSTRUCTION,
    )
    raw = chat_json(
        system=TEAMLEAD_GATE1_SYSTEM,
        user=user_msg,
        label="gate1-team_lead",
        max_tokens=1500,
    )
    # 안전망: LLM 이 가끔 feedback_memo 를 checks 안에 넣음 (Gate 2 에서도 발생했던 패턴)
    checks = raw.get("checks") or {}
    raw["checks"] = {k: v for k, v in checks.items() if isinstance(v, dict)}
    if "feedback_memo" in checks and isinstance(checks["feedback_memo"], str) and not raw.get("feedback_memo"):
        raw["feedback_memo"] = checks["feedback_memo"]
    return Gate1TeamLeadVerdict.model_validate(raw)


def _aggregate_round(
    team_lead: Gate1TeamLeadVerdict,
    pm: dict[str, Any],
    tech: dict[str, Any],
) -> Gate1RoundResult:
    """3 검증자 결과를 종합해 최종 verdict 와 feedback 을 만든다.

    종합 규칙: 누구라도 ok=false 가 있으면 final_verdict = fail.
    """
    issues: list[str] = []

    for name, ck in team_lead.checks.items():
        if not ck.ok:
            issues.append(f"[Team Lead/{name}] {ck.issue}")
    for name in ("planning_usability", "mvp_realism"):
        ck = pm.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[PM/{name}] {ck.get('issue', '')}")
    for name in ("constitution_buildability", "constraint_fit"):
        ck = tech.get(name) or {}
        if not ck.get("ok", True):
            issues.append(f"[Tech/{name}] {ck.get('issue', '')}")

    final = "pass" if not issues else "fail"
    aggregated = team_lead.feedback_memo if final == "fail" and team_lead.feedback_memo else ""
    if issues:
        aggregated = (
            (team_lead.feedback_memo + "\n\n" if team_lead.feedback_memo else "")
            + "추가 검토 의견:\n- "
            + "\n- ".join(issues)
        )

    return Gate1RoundResult(
        team_lead=team_lead,
        pm_review=pm,
        tech_review=tech,
        final_verdict=final,
        aggregated_feedback=aggregated,
    )


def run_gate1(
    harness_input: HarnessInput,
    constitution: ConstitutionResult,
) -> Gate1Result:
    """헌법 검증 1회 수행 (재시도 없음).

    재시도/조건부 통과 분기는 LangGraph conditional_edges (Phase B) 가 책임.
    """
    print("[Gate 1] Team Lead + PM + Tech 병렬 검증 시작")
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_orch = pool.submit(_team_lead_judge, harness_input, constitution.markdown)
        f_pm = pool.submit(pm_review_gate1, harness_input, constitution.markdown)
        f_tech = pool.submit(tech_review_gate1, harness_input, constitution.markdown)
        orch = f_orch.result()
        pm = f_pm.result()
        tech = f_tech.result()

    round_result = _aggregate_round(orch, pm, tech)

    final = (
        GateResult.PASS_
        if round_result.final_verdict == "pass"
        else GateResult.FAIL
    )

    return Gate1Result(
        final_verdict=final,
        constitution=constitution,
        round_result=round_result,
    )