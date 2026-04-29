"""LangGraph 기반 하네스 워크플로우 정의.

기획서 3.4.2 의 워크플로우를 LangGraph StateGraph 로 표현.
Gate fail 시 작성 노드로 돌아가는 conditional_edges 포함.

흐름:
    START → constitution → gate1
       gate1.PASS               → service_brief → mvp_scope → user_flow → build_plan → qa_plan → gate2
       gate1.FAIL  (1회차)       → constitution (재작성)
       gate1.FAIL  (2회차)       → 노드가 verdict 를 CONDITIONAL_PASS 로 덮어씀 → service_brief

       gate2.PASS                → END
       gate2.FAIL  (1회차)       → service_brief (5종 재작성)
       gate2.FAIL  (2회차)       → 노드가 verdict 를 CONDITIONAL_PASS 로 덮어씀 → END

기획서 4.2.5 ④ "동일 Gate 는 최대 2회까지 수행" — retry 1회.

------------------------------------------------------------
설계 패턴: "조건문은 노드, 라우터는 매핑"
------------------------------------------------------------
처음엔 라우터 함수에 "if retry<1 → constitution / else → service_brief" 같은
조건문을 다 넣을까 싶지만, 그 방식은 책임이 흩어집니다.

본 그래프는 다음 두 단계로 책임 분리:

(1) **노드** 가 "이번이 N차 시도였고 어떤 verdict 가 최종이다" 까지 결정.
    - retry_count 증가
    - 2회차 fail 이면 verdict 를 FAIL → CONDITIONAL_PASS 로 덮어씀
    - risk_memo 작성

(2) **라우터** 는 verdict 값만 보고 미리 정의된 매핑(dict)을 따라 분기.
    - if/else 가 아니라 "verdict → 다음 노드" 의 단순 매핑
    - PASS / CONDITIONAL_PASS → 다음 단계
    - FAIL → 작성 노드로 돌아가기

이러면 라우터 함수는 단순해지고 (분기 로직이 한 곳에 집중), 노드는
"이 단계의 최종 판정" 책임만 명확히 가짐. LangGraph 의 권장 패턴.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.edu_agent import write_constitution
from src.agents.pm_agent import (
    write_service_brief,
    write_mvp_scope,
    write_user_flow,
    write_qa_plan,
    write_data_schema,
    write_state_machine,
    write_interface_spec,
)
from src.agents.tech_agent import write_build_plan
from src.agents.prompt_agent import write_prompt_spec
from src.gates.gate1 import Gate1Result, run_gate1
from src.gates.gate2 import Gate2Result, PlanningArtifacts, run_gate2
from src.gates.gate3 import Gate3Result, run_gate3
from src.schemas.input_schema import HarnessInput
from src.schemas.workflow_state import GateResult


class HarnessState(TypedDict, total=False):
    """그래프가 들고 다니는 상태."""

    # 입력
    harness_input: HarnessInput

    # Step 2 — 헌법
    constitution_md: str

    # Gate 1
    gate1_result: Gate1Result
    gate1_retry_count: int  # 0 (초기) → 1 (1차 검증 후) → 2 (2차 검증 후)
    gate1_risk_memo: str  # CONDITIONAL_PASS 시 잔존 issue 기록

    # Step 3 — 기획문서 5종
    service_brief_md: str
    mvp_scope_md: str
    user_flow_md: str
    build_plan_md: str
    qa_plan_md: str

    # Gate 2
    gate2_result: Gate2Result
    gate2_retry_count: int
    gate2_risk_memo: str

    # Step 4 — 구현 명세서 4종
    data_schema_json: str   # JSON 텍스트 (output_format=JSON)
    state_machine_md: str
    prompt_spec_md: str
    interface_spec_md: str

    # Gate 3
    gate3_result: Gate3Result
    gate3_retry_count: int
    gate3_risk_memo: str


# ============================================================
# 노드 함수들
# ============================================================


def node_constitution(state: HarnessState) -> dict[str, Any]:
    """Step 2 — Edu Agent 가 헌법 작성."""
    result = write_constitution(state["harness_input"])
    return {"constitution_md": result.markdown}


def node_gate1(state: HarnessState) -> dict[str, Any]:
    """Gate 1 — 헌법 검증 (다중 검증자).

    노드 책임:
    - 검증 1회 실행
    - retry_count 증가
    - **2회차 fail 이면 verdict 를 CONDITIONAL_PASS 로 덮어씀** (라우터가 단순 매핑하도록)
    - risk_memo 작성
    """
    from src.agents.edu_agent import ConstitutionResult

    constitution = ConstitutionResult(
        markdown=state["constitution_md"], stage_outputs={}
    )
    result = run_gate1(state["harness_input"], constitution)

    retry_before = state.get("gate1_retry_count", 0)
    updates: dict[str, Any] = {
        "gate1_result": result,
        "gate1_retry_count": retry_before + 1,
    }

    # 2회차도 fail → CONDITIONAL_PASS 로 verdict 덮어쓰기 + risk_memo
    if result.final_verdict == GateResult.FAIL and retry_before >= 1:
        risk_issues = result.round_result.issues_only()
        updates["gate1_risk_memo"] = (
            "Gate 1 재검토 후에도 fail. 잔존 issue: " + " | ".join(risk_issues)
        )
        updates["gate1_result"] = replace(
            result, final_verdict=GateResult.CONDITIONAL_PASS
        )

    return updates


def node_service_brief(state: HarnessState) -> dict[str, Any]:
    art = write_service_brief(
        state["harness_input"], constitution_md=state["constitution_md"]
    )
    return {"service_brief_md": art.markdown}


def node_mvp_scope(state: HarnessState) -> dict[str, Any]:
    art = write_mvp_scope(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        service_brief_md=state["service_brief_md"],
    )
    return {"mvp_scope_md": art.markdown}


def node_user_flow(state: HarnessState) -> dict[str, Any]:
    art = write_user_flow(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
    )
    return {"user_flow_md": art.markdown}


def node_build_plan(state: HarnessState) -> dict[str, Any]:
    art = write_build_plan(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
    )
    return {"build_plan_md": art.markdown}


def node_qa_plan(state: HarnessState) -> dict[str, Any]:
    art = write_qa_plan(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
        build_plan_md=state["build_plan_md"],
    )
    return {"qa_plan_md": art.markdown}


def node_gate2(state: HarnessState) -> dict[str, Any]:
    """Gate 2 — 기획문서 5종 다중 검증.

    node_gate1 과 동일 패턴: 2회차 fail 이면 CONDITIONAL_PASS 로 덮어쓰기.
    """
    from src.agents.pm_agent import ArtifactOutput

    artifacts = PlanningArtifacts(
        service_brief=ArtifactOutput("service_brief", state["service_brief_md"]),
        mvp_scope=ArtifactOutput("mvp_scope", state["mvp_scope_md"]),
        user_flow=ArtifactOutput("user_flow", state["user_flow_md"]),
        build_plan=ArtifactOutput("build_plan", state["build_plan_md"]),
        qa_plan=ArtifactOutput("qa_plan", state["qa_plan_md"]),
    )
    result = run_gate2(
        state["harness_input"], state["constitution_md"], artifacts
    )

    retry_before = state.get("gate2_retry_count", 0)
    updates: dict[str, Any] = {
        "gate2_result": result,
        "gate2_retry_count": retry_before + 1,
    }

    if result.final_verdict == GateResult.FAIL and retry_before >= 1:
        risk_issues = result.rounds[-1].issues_only()
        updates["gate2_risk_memo"] = (
            "Gate 2 재검토 후에도 fail. 잔존 issue: " + " | ".join(risk_issues)
        )
        updates["gate2_result"] = replace(
            result, final_verdict=GateResult.CONDITIONAL_PASS
        )

    return updates


def node_data_schema(state: HarnessState) -> dict[str, Any]:
    art = write_data_schema(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
        build_plan_md=state["build_plan_md"],
    )
    return {"data_schema_json": art.markdown}


def node_state_machine(state: HarnessState) -> dict[str, Any]:
    art = write_state_machine(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        user_flow_md=state["user_flow_md"],
        qa_plan_md=state["qa_plan_md"],
        build_plan_md=state["build_plan_md"],
        mvp_scope_md=state["mvp_scope_md"],
        data_schema_json=state["data_schema_json"],
    )
    return {"state_machine_md": art.markdown}


def node_prompt_spec(state: HarnessState) -> dict[str, Any]:
    art = write_prompt_spec(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        data_schema_json=state["data_schema_json"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
        qa_plan_md=state["qa_plan_md"],
    )
    return {"prompt_spec_md": art.markdown}


def node_interface_spec(state: HarnessState) -> dict[str, Any]:
    art = write_interface_spec(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        user_flow_md=state["user_flow_md"],
        data_schema_json=state["data_schema_json"],
        build_plan_md=state["build_plan_md"],
        state_machine_md=state["state_machine_md"],
    )
    return {"interface_spec_md": art.markdown}


def node_gate3(state: HarnessState) -> dict[str, Any]:
    """Gate 3 — 구현 명세서 4종 검증.

    node_gate1/2 와 동일 패턴: 2회차 fail 이면 CONDITIONAL_PASS 로 덮어쓰기.
    """
    impl_specs = {
        "Data Schema": state["data_schema_json"],
        "State Machine": state["state_machine_md"],
        "Prompt Spec": state["prompt_spec_md"],
        "Interface Spec": state["interface_spec_md"],
    }
    result = run_gate3(state["constitution_md"], impl_specs)

    retry_before = state.get("gate3_retry_count", 0)
    updates: dict[str, Any] = {
        "gate3_result": result,
        "gate3_retry_count": retry_before + 1,
    }

    if result.final_verdict == GateResult.FAIL and retry_before >= 1:
        risk_issues = result.issues_only()
        updates["gate3_risk_memo"] = (
            "Gate 3 재검토 후에도 fail. 잔존 issue: " + " | ".join(risk_issues)
        )
        updates["gate3_result"] = replace(
            result, final_verdict=GateResult.CONDITIONAL_PASS
        )

    return updates


# ============================================================
# Conditional edges — 라우터 함수
# ============================================================
# 라우터는 단순 매핑만 한다 (조건문 X). 노드가 verdict 를 이미 정리해뒀으므로
# verdict 값을 미리 정의된 분기로 매핑하면 끝.
# ============================================================


def route_after_gate1(state: HarnessState) -> Literal["service_brief", "constitution"]:
    """Gate 1 후 다음 노드 매핑.

    PASS / CONDITIONAL_PASS → service_brief (다음 단계)
    FAIL                    → constitution  (재작성)
    """
    verdict = state["gate1_result"].final_verdict
    return {
        GateResult.PASS_:             "service_brief",
        GateResult.CONDITIONAL_PASS:  "service_brief",
        GateResult.FAIL:              "constitution",
    }[verdict]


def route_after_gate2(state: HarnessState) -> Literal["service_brief", "data_schema"]:
    """Gate 2 후 다음 노드 매핑.

    PASS / CONDITIONAL_PASS → data_schema (Step 4 시작)
    FAIL                    → service_brief (5종 재작성)
    """
    verdict = state["gate2_result"].final_verdict
    return {
        GateResult.PASS_:             "data_schema",
        GateResult.CONDITIONAL_PASS:  "data_schema",
        GateResult.FAIL:              "service_brief",
    }[verdict]


def route_after_gate3(state: HarnessState) -> Literal["data_schema", "__end__"]:
    """Gate 3 후 다음 노드 매핑.

    PASS / CONDITIONAL_PASS → __end__     (전체 완료)
    FAIL                    → data_schema (4종 재작성)
    """
    verdict = state["gate3_result"].final_verdict
    return {
        GateResult.PASS_:             "__end__",
        GateResult.CONDITIONAL_PASS:  "__end__",
        GateResult.FAIL:              "data_schema",
    }[verdict]


# ============================================================
# 그래프 빌드
# ============================================================


def build_harness_graph() -> Any:
    """하네스 워크플로우 그래프 빌드 + 컴파일."""
    g = StateGraph(HarnessState)

    # Step 2
    g.add_node("constitution", node_constitution)
    g.add_node("gate1", node_gate1)
    # Step 3
    g.add_node("service_brief", node_service_brief)
    g.add_node("mvp_scope", node_mvp_scope)
    g.add_node("user_flow", node_user_flow)
    g.add_node("build_plan", node_build_plan)
    g.add_node("qa_plan", node_qa_plan)
    g.add_node("gate2", node_gate2)
    # Step 4
    g.add_node("data_schema", node_data_schema)
    g.add_node("state_machine", node_state_machine)
    g.add_node("prompt_spec", node_prompt_spec)
    g.add_node("interface_spec", node_interface_spec)
    g.add_node("gate3", node_gate3)

    g.add_edge(START, "constitution")
    g.add_edge("constitution", "gate1")

    # Gate 1 분기
    g.add_conditional_edges(
        "gate1",
        route_after_gate1,
        {
            "service_brief": "service_brief",
            "constitution":  "constitution",
        },
    )

    g.add_edge("service_brief", "mvp_scope")
    g.add_edge("mvp_scope", "user_flow")
    g.add_edge("user_flow", "build_plan")
    g.add_edge("build_plan", "qa_plan")
    g.add_edge("qa_plan", "gate2")

    # Gate 2 분기 — PASS → Step 4, FAIL → 5종 재작성
    g.add_conditional_edges(
        "gate2",
        route_after_gate2,
        {
            "service_brief": "service_brief",
            "data_schema":   "data_schema",
        },
    )

    g.add_edge("data_schema", "state_machine")
    g.add_edge("state_machine", "prompt_spec")
    g.add_edge("prompt_spec", "interface_spec")
    g.add_edge("interface_spec", "gate3")

    # Gate 3 분기 — PASS → END, FAIL → 4종 재작성
    g.add_conditional_edges(
        "gate3",
        route_after_gate3,
        {
            "data_schema": "data_schema",
            "__end__":     END,
        },
    )

    return g.compile()


HARNESS_GRAPH = build_harness_graph()