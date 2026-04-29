"""Gate 3 — 구현 명세서 4종 검증 (Orchestrator 단독 버전).

기획서 5.4 의 검증 구조에서 Orchestrator 4항목 우선 구현.
향후 Tech Agent review 추가 예정 (TODO: _TODO.md 참조).

fail 시 data_schema 노드부터 4종 재작성 → 재검증 (1회까지).
재시도 후에도 fail 이면 CONDITIONAL_PASS + risk_memo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat_json
from src.prompts.orchestrator_gate3 import GATE3_INSTRUCTION, ORCHESTRATOR_GATE3_SYSTEM
from src.schemas.workflow_state import GateResult


class GateCheck(BaseModel):
    ok: bool
    issue: str = ""


class Gate3OrchestratorVerdict(BaseModel):
    """Orchestrator 의 직접 검증 4항목 응답."""

    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


@dataclass
class Gate3Result:
    final_verdict: GateResult
    orchestrator_verdict: Gate3OrchestratorVerdict
    risk_memo: str = ""

    def issues_only(self) -> list[str]:
        out: list[str] = []
        for name, ck in self.orchestrator_verdict.checks.items():
            if not ck.ok:
                out.append(f"Orchestrator/{name}: {ck.issue}")
        return out

    def to_log_markdown(self) -> str:
        lines = [f"## Gate 3 결과: **{self.final_verdict.value}**", ""]
        lines.append("**Orchestrator 직접 검증:**")
        for name, ck in self.orchestrator_verdict.checks.items():
            mark = "✅" if ck.ok else "❌"
            lines.append(f"- {mark} {name}: {ck.issue or '(통과)'}")
        if self.orchestrator_verdict.feedback_memo:
            lines.append("")
            lines.append(f"**feedback_memo:** {self.orchestrator_verdict.feedback_memo}")
        if self.risk_memo:
            lines.append("")
            lines.append(f"**risk_memo:** {self.risk_memo}")
        return "\n".join(lines)


def _orchestrator_judge(
    constitution_md: str,
    impl_specs: dict[str, str],
) -> Gate3OrchestratorVerdict:
    ctx = PromptContext(
        global_blocks={"헌법 (Constitution)": constitution_md},
        primary_blocks=impl_specs,
    )
    user_msg = build_user_prompt(context=ctx, instruction=GATE3_INSTRUCTION)
    raw = chat_json(
        system=ORCHESTRATOR_GATE3_SYSTEM,
        user=user_msg,
        label="gate3-orchestrator",
        max_tokens=1500,
    )
    checks = raw.get("checks") or {}
    raw["checks"] = {k: v for k, v in checks.items() if isinstance(v, dict)}
    if "feedback_memo" in checks and isinstance(checks["feedback_memo"], str) and not raw.get("feedback_memo"):
        raw["feedback_memo"] = checks["feedback_memo"]
    return Gate3OrchestratorVerdict.model_validate(raw)


def run_gate3(
    constitution_md: str,
    impl_specs: dict[str, str],
) -> Gate3Result:
    """구현 명세서 4종 검증 1회 수행.

    재시도/조건부 통과 분기는 LangGraph conditional_edges 가 책임.
    harness_input 불필요 — 실행 제약은 Gate 2 통과 시 기획 5종에 이미 반영됨.
    """
    print("[Gate 3] Orchestrator 직접 검증")
    orch = _orchestrator_judge(constitution_md, impl_specs)
    final = GateResult.PASS_ if orch.verdict == "pass" else GateResult.FAIL
    return Gate3Result(final_verdict=final, orchestrator_verdict=orch)
