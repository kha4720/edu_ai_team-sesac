"""Gate 1 — 헌법(Constitution) 검증.

기획서 5.2.6 의 검증 항목을 Orchestrator 가 LLM-as-judge 방식으로 직접 판단.
fail 시 feedback_memo 를 Edu Agent 에게 전달하고 재작성 → 재검증 (1회까지).
재시도 후에도 fail 이면 conditional_pass + risk_memo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from src.agents.edu_agent import ConstitutionResult, write_constitution
from src.llm.prompt_builder import PromptContext, build_user_prompt
from src.llm.solar import chat_json
from src.prompts.orchestrator_gate1 import (
    GATE1_INSTRUCTION,
    ORCHESTRATOR_GATE1_SYSTEM,
)
from src.schemas.input_schema import HarnessInput
from src.schemas.workflow_state import GateResult


# === Gate 1 검증 응답 스키마 (LLM 의 JSON 응답을 검증) ===


class GateCheck(BaseModel):
    ok: bool
    issue: str = ""


class Gate1Verdict(BaseModel):
    verdict: Literal["pass", "fail"]
    checks: dict[str, GateCheck] = Field(default_factory=dict)
    feedback_memo: str = ""


# === 최종 결과 컨테이너 (재시도 이력 포함) ===


@dataclass
class Gate1Result:
    final_verdict: GateResult  # PASS_ / FAIL / CONDITIONAL_PASS
    constitution: ConstitutionResult  # 최종 헌법 (재작성 후 버전이 들어있을 수 있음)
    attempts: list[Gate1Verdict]  # 검증 시도 이력 (1회 또는 2회)
    risk_memo: str = ""

    def to_log_markdown(self) -> str:
        """워크플로우 로그용 짧은 요약."""
        lines = [f"## Gate 1 결과: **{self.final_verdict.value}**", ""]
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


# === 핵심 함수 ===


def _judge_once(
    harness_input: HarnessInput, constitution_md: str
) -> Gate1Verdict:
    """헌법 1편을 받아 Orchestrator LLM 으로 1회 검증한다."""
    ctx = PromptContext(
        global_blocks={"사용자 입력": harness_input.to_global_context()},
        primary_blocks={"검증 대상 헌법": constitution_md},
    )
    user_msg = build_user_prompt(
        context=ctx,
        instruction=GATE1_INSTRUCTION,
    )
    raw = chat_json(
        system=ORCHESTRATOR_GATE1_SYSTEM,
        user=user_msg,
        label="gate1-judge",
        max_tokens=1500,
    )
    return Gate1Verdict.model_validate(raw)


def run_gate1(
    harness_input: HarnessInput,
    constitution: ConstitutionResult,
    *,
    max_retries: int = 1,
) -> Gate1Result:
    """헌법 검증 + 재시도까지 처리한다.

    흐름:
        1) 1차 검증
        2) pass → 종료
        3) fail → feedback_memo 를 Edu Agent 에게 전달해 헌법 재작성
        4) 2차 검증
        5) pass → 종료, fail → conditional_pass + risk_memo

    Args:
        harness_input: 사용자 입력
        constitution: write_constitution 으로 만든 초안 헌법
        max_retries: 재시도 한도 (기본 1, 기획서 4.2.5 ④ 규칙)
    """
    attempts: list[Gate1Verdict] = []
    current = constitution

    # 1차 검증
    print("[Gate 1] 1차 검증 시작")
    verdict1 = _judge_once(harness_input, current.markdown)
    attempts.append(verdict1)
    if verdict1.verdict == "pass":
        return Gate1Result(
            final_verdict=GateResult.PASS_,
            constitution=current,
            attempts=attempts,
        )

    # 재시도
    if max_retries < 1:
        return Gate1Result(
            final_verdict=GateResult.FAIL,
            constitution=current,
            attempts=attempts,
        )

    print(f"[Gate 1] FAIL → 재작성 시작 (feedback: {verdict1.feedback_memo[:80]}...)")
    current = _rewrite_constitution_with_feedback(harness_input, current, verdict1.feedback_memo)

    print("[Gate 1] 2차 검증 시작")
    verdict2 = _judge_once(harness_input, current.markdown)
    attempts.append(verdict2)
    if verdict2.verdict == "pass":
        return Gate1Result(
            final_verdict=GateResult.PASS_,
            constitution=current,
            attempts=attempts,
        )

    # 2차도 fail → conditional_pass
    risk = (
        "Gate 1 동일 검증 항목 2회 연속 미흡. "
        f"잔존 issue: "
        + "; ".join(
            f"{name}: {ck.issue}"
            for name, ck in verdict2.checks.items()
            if not ck.ok
        )
    )
    return Gate1Result(
        final_verdict=GateResult.CONDITIONAL_PASS,
        constitution=current,
        attempts=attempts,
        risk_memo=risk,
    )


def _rewrite_constitution_with_feedback(
    harness_input: HarnessInput,
    previous: ConstitutionResult,
    feedback_memo: str,
) -> ConstitutionResult:
    """fail 후 Edu Agent 가 feedback_memo 를 받아 헌법을 재작성.

    MVP 단순화: write_constitution 을 통째로 다시 호출하되, 시스템 프롬프트 외에
    "직전 헌법 + feedback_memo 를 반영해 다시 쓴다" 는 컨텍스트를 user 메시지에 추가하는 게 이상적.
    그러나 write_constitution 은 5번 호출의 묶음이라 외부에서 재진입이 까다롭다.
    Phase 1 에서는 **간단히 다시 통째 생성** 하고, feedback_memo 는 다음 라운드 디버깅 자료로만 사용한다.
    (실제 발표 시연에서 1차 fail 이 발생하면 retry 가 보일 것 — Phase 2 에서 정교화 가능)
    """
    # MEMO: 정교한 구현은 Phase 2 (발표 후) 로 미룸. 여기선 단순 재호출.
    _ = previous, feedback_memo  # 의도적으로 미사용 — 다음 phase 에서 활용
    return write_constitution(harness_input)
