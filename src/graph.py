"""LangGraph 기반 하네스 워크플로우 정의.

기획서 3.4.2 의 워크플로우를 LangGraph StateGraph 로 표현한다.

흐름 (선형):
    START → constitution → gate1
          → service_brief → mvp_scope → user_flow → build_plan → qa_plan
          → gate2 → END

향후 확장 (TODO):
- Gate fail 시 작성 노드로 돌아가는 conditional_edges (현재는 게이트 내부 retry 로직으로 대체)
- Step 4 구현 명세서 4종 노드 추가
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.edu_agent import write_constitution
from src.agents.pm_agent import (
    write_mvp_scope,
    write_qa_plan,
    write_service_brief,
    write_user_flow,
)
from src.agents.tech_agent import write_build_plan
from src.gates.gate1 import Gate1Result, run_gate1
from src.gates.gate2 import Gate2Result, PlanningArtifacts, run_gate2
from src.schemas.input_schema import HarnessInput


class HarnessState(TypedDict, total=False):
    """그래프가 들고 다니는 상태.

    각 노드는 이 State 의 일부 필드를 갱신해서 반환한다 (LangGraph 가 자동 머지).
    `total=False` 로 두어 단계별로 점진적 채움이 가능.
    """

    # 입력 (그래프 시작 시 주입)
    harness_input: HarnessInput

    # Step 2 — 헌법
    constitution_md: str

    # Gate 1
    gate1_result: Gate1Result

    # Step 3 — 기획문서 5종
    service_brief_md: str
    mvp_scope_md: str
    user_flow_md: str
    build_plan_md: str
    qa_plan_md: str

    # Gate 2
    gate2_result: Gate2Result


# ============================================================
# 노드 함수들 — 각 노드는 State 일부 필드만 갱신해 반환
# ============================================================


def node_constitution(state: HarnessState) -> dict[str, Any]:
    """Step 2 — Edu Agent 가 헌법 작성."""
    result = write_constitution(state["harness_input"])
    return {"constitution_md": result.markdown}


def node_gate1(state: HarnessState) -> dict[str, Any]:
    """Gate 1 — 헌법 검증."""
    from src.agents.edu_agent import ConstitutionResult

    constitution = ConstitutionResult(
        markdown=state["constitution_md"], stage_outputs={}
    )
    result = run_gate1(state["harness_input"], constitution, max_retries=0)
    # 재작성 발생 시 갱신된 헌법을 반영
    return {
        "gate1_result": result,
        "constitution_md": result.constitution.markdown,
    }


def node_service_brief(state: HarnessState) -> dict[str, Any]:
    """Step 3-1 — PM Agent / Service Brief."""
    art = write_service_brief(
        state["harness_input"],
        constitution_md=state["constitution_md"],
    )
    return {"service_brief_md": art.markdown}


def node_mvp_scope(state: HarnessState) -> dict[str, Any]:
    """Step 3-2 — PM Agent / MVP Scope."""
    art = write_mvp_scope(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        service_brief_md=state["service_brief_md"],
    )
    return {"mvp_scope_md": art.markdown}


def node_user_flow(state: HarnessState) -> dict[str, Any]:
    """Step 3-3 — PM Agent / User Flow."""
    art = write_user_flow(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
    )
    return {"user_flow_md": art.markdown}


def node_build_plan(state: HarnessState) -> dict[str, Any]:
    """Step 3-4 — Tech Agent / Build Plan."""
    art = write_build_plan(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
    )
    return {"build_plan_md": art.markdown}


def node_qa_plan(state: HarnessState) -> dict[str, Any]:
    """Step 3-5 — PM Agent / QA Plan."""
    art = write_qa_plan(
        state["harness_input"],
        constitution_md=state["constitution_md"],
        mvp_scope_md=state["mvp_scope_md"],
        user_flow_md=state["user_flow_md"],
        build_plan_md=state["build_plan_md"],
    )
    return {"qa_plan_md": art.markdown}


def node_gate2(state: HarnessState) -> dict[str, Any]:
    """Gate 2 — Orchestrator + Edu + Tech 다중 검증."""
    from src.agents.pm_agent import ArtifactOutput

    artifacts = PlanningArtifacts(
        service_brief=ArtifactOutput("service_brief", state["service_brief_md"]),
        mvp_scope=ArtifactOutput("mvp_scope", state["mvp_scope_md"]),
        user_flow=ArtifactOutput("user_flow", state["user_flow_md"]),
        build_plan=ArtifactOutput("build_plan", state["build_plan_md"]),
        qa_plan=ArtifactOutput("qa_plan", state["qa_plan_md"]),
    )
    result = run_gate2(
        state["harness_input"],
        state["constitution_md"],
        artifacts,
        max_retries=0,
    )
    # 재작성 발생 시 갱신된 5종 반영
    final = result.artifacts
    return {
        "gate2_result": result,
        "service_brief_md": final.service_brief.markdown,
        "mvp_scope_md": final.mvp_scope.markdown,
        "user_flow_md": final.user_flow.markdown,
        "build_plan_md": final.build_plan.markdown,
        "qa_plan_md": final.qa_plan.markdown,
    }


# ============================================================
# 그래프 빌드
# ============================================================


def build_harness_graph() -> Any:
    """하네스 워크플로우 그래프를 빌드해서 컴파일된 인스턴스 반환."""
    g = StateGraph(HarnessState)

    # 노드 등록
    g.add_node("constitution", node_constitution)
    g.add_node("gate1", node_gate1)
    g.add_node("service_brief", node_service_brief)
    g.add_node("mvp_scope", node_mvp_scope)
    g.add_node("user_flow", node_user_flow)
    g.add_node("build_plan", node_build_plan)
    g.add_node("qa_plan", node_qa_plan)
    g.add_node("gate2", node_gate2)

    # 엣지 (선형)
    g.add_edge(START, "constitution")
    g.add_edge("constitution", "gate1")
    g.add_edge("gate1", "service_brief")
    g.add_edge("service_brief", "mvp_scope")
    g.add_edge("mvp_scope", "user_flow")
    g.add_edge("user_flow", "build_plan")
    g.add_edge("build_plan", "qa_plan")
    g.add_edge("qa_plan", "gate2")
    g.add_edge("gate2", END)

    return g.compile()


# 컴파일된 그래프 (re-use 용 단일 인스턴스)
HARNESS_GRAPH = build_harness_graph()