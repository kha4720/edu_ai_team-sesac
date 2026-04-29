"""하네스 통합 진입점 (LangGraph 기반).

`run_pipeline(harness_input)` 한 번 호출로 그래프 전체를 실행한다:
1. constitution (Edu Agent)
2. gate1 (Orchestrator)
3. service_brief / mvp_scope / user_flow / build_plan / qa_plan (PM/Tech)
4. gate2 (Orchestrator + Edu + Tech 다중 검증자)
5. 산출물 + 워크플로우 로그를 outputs/<프로젝트명>_<timestamp>/ 에 저장

내부 구현은 `src.graph.HARNESS_GRAPH.stream()` 을 사용해 노드 단위 이벤트를
콜백으로 emit. UI 가 단계별 산출물을 즉시 받을 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.gates.gate1 import Gate1Result
from src.gates.gate2 import Gate2Result, PlanningArtifacts
from src.gates.gate3 import Gate3Result
from src.graph import HARNESS_GRAPH
from src.schemas.input_schema import HarnessInput

ProgressCallback = Callable[[str, str], None]
"""(stage_id, message) → None. UI 가 진행 상황 표시에 사용."""

ArtifactCallback = Callable[[str, str], None]
"""(artifact_id, markdown) → None. 산출물 1개 생성 직후 UI 에 즉시 푸시."""


@dataclass
class PipelineResult:
    """파이프라인 실행 결과 묶음."""

    output_dir: Path
    constitution_md: str
    gate1: Gate1Result
    artifacts: PlanningArtifacts
    gate2: Gate2Result
    gate3: Gate3Result
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    workflow_log_path: Path | None = None


def _noop_progress(stage: str, message: str) -> None:
    print(f"[{stage}] {message}")


# 노드명 → 사람이 읽기 좋은 진행 메시지
_NODE_MESSAGES = {
    "constitution": ("constitution", "Edu Agent — 헌법 작성 중 (5번 호출, 약 20초)"),
    "gate1": ("gate1", "Orchestrator — Gate 1 (헌법 검증)"),
    "service_brief": ("service_brief", "PM Agent — Service Brief 작성"),
    "mvp_scope": ("mvp_scope", "PM Agent — MVP Scope 작성"),
    "user_flow": ("user_flow", "PM Agent — User Flow 작성"),
    "build_plan": ("build_plan", "Tech Agent — Build Plan 작성"),
    "qa_plan": ("qa_plan", "PM Agent — QA Plan 작성"),
    "gate2": ("gate2", "Orchestrator + Edu + Tech — Gate 2 (5종 다중 검증)"),
    "data_schema": ("data_schema", "PM Agent — Data Schema 작성"),
    "state_machine": ("state_machine", "PM Agent — State Machine 작성"),
    "prompt_spec": ("prompt_spec", "Prompt Agent — Prompt Spec 작성"),
    "interface_spec": ("interface_spec", "PM Agent — Interface Spec 작성"),
    "gate3": ("gate3", "Orchestrator — Gate 3 (구현 명세서 4종 검증)"),
}

# 노드 update 안에 들어있는 markdown/json 필드 → artifact_id 매핑
_NODE_TO_ARTIFACT = {
    "constitution_md": "constitution",
    "service_brief_md": "service_brief",
    "mvp_scope_md": "mvp_scope",
    "user_flow_md": "user_flow",
    "build_plan_md": "build_plan",
    "qa_plan_md": "qa_plan",
    "data_schema_json": "data_schema",
    "state_machine_md": "state_machine",
    "prompt_spec_md": "prompt_spec",
    "interface_spec_md": "interface_spec",
}


def run_pipeline(
    harness_input: HarnessInput,
    *,
    project_slug: str = "harness",
    on_progress: ProgressCallback | None = None,
    on_artifact: ArtifactCallback | None = None,
    output_root: Path | str = "outputs",
) -> PipelineResult:
    """하네스 전체 파이프라인 실행 (LangGraph 기반).

    Args:
        harness_input: 사용자 입력.
        project_slug: 출력 폴더 prefix (예: "question_coach").
        on_progress: 진행 상황 보고 콜백. None 이면 print.
        on_artifact: 산출물 1개 완성 직후 호출되는 콜백 (artifact_id, markdown).
        output_root: 출력 루트 폴더 (기본 "outputs").
    """
    progress = on_progress or _noop_progress
    push_artifact = on_artifact or (lambda a, m: None)

    # 출력 폴더 준비
    progress("init", "출력 폴더 준비")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_root) / f"{project_slug}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 그래프 실행 — stream 으로 노드 단위 이벤트 받음
    initial_state = {"harness_input": harness_input}
    final_state: dict[str, object] = {}

    for chunk in HARNESS_GRAPH.stream(initial_state):
        # chunk = {"노드명": {"필드명": 값, ...}}
        for node_name, updates in chunk.items():
            # 진행 메시지
            if node_name in _NODE_MESSAGES:
                stage_id, msg = _NODE_MESSAGES[node_name]
                progress(stage_id, msg + " — 시작")

            # 누적 state 업데이트
            final_state.update(updates)

            # 산출물 콜백 (markdown 필드가 있으면 즉시 푸시)
            for field_name, artifact_id in _NODE_TO_ARTIFACT.items():
                if field_name in updates and isinstance(updates[field_name], str):
                    push_artifact(artifact_id, updates[field_name])

            # Gate 결과는 별도 처리 (markdown 변환)
            if node_name == "gate1" and "gate1_result" in updates:
                push_artifact("gate1_log", updates["gate1_result"].to_log_markdown())
            if node_name == "gate2" and "gate2_result" in updates:
                push_artifact("gate2_log", updates["gate2_result"].to_log_markdown())
            if node_name == "gate3" and "gate3_result" in updates:
                push_artifact("gate3_log", updates["gate3_result"].to_log_markdown())

    # 최종 state 에서 결과 추출
    constitution_md = str(final_state["constitution_md"])
    gate1: Gate1Result = final_state["gate1_result"]  # type: ignore[assignment]
    gate2: Gate2Result = final_state["gate2_result"]  # type: ignore[assignment]
    gate3: Gate3Result = final_state["gate3_result"]  # type: ignore[assignment]
    artifacts = gate2.artifacts
    data_schema_json = str(final_state["data_schema_json"])
    state_machine_md = str(final_state["state_machine_md"])
    prompt_spec_md = str(final_state["prompt_spec_md"])
    interface_spec_md = str(final_state["interface_spec_md"])

    # 디스크 저장
    progress("save", "산출물 디스크 저장")
    (out_dir / "constitution.md").write_text(constitution_md, encoding="utf-8")
    (out_dir / "service_brief.md").write_text(artifacts.service_brief.markdown, encoding="utf-8")
    (out_dir / "mvp_scope.md").write_text(artifacts.mvp_scope.markdown, encoding="utf-8")
    (out_dir / "user_flow.md").write_text(artifacts.user_flow.markdown, encoding="utf-8")
    (out_dir / "build_plan.md").write_text(artifacts.build_plan.markdown, encoding="utf-8")
    (out_dir / "qa_plan.md").write_text(artifacts.qa_plan.markdown, encoding="utf-8")
    (out_dir / "data_schema.json").write_text(data_schema_json, encoding="utf-8")
    (out_dir / "state_machine.md").write_text(state_machine_md, encoding="utf-8")
    (out_dir / "prompt_spec.md").write_text(prompt_spec_md, encoding="utf-8")
    (out_dir / "interface_spec.md").write_text(interface_spec_md, encoding="utf-8")

    log_md = gate1.to_log_markdown() + "\n\n" + gate2.to_log_markdown() + "\n\n" + gate3.to_log_markdown()
    log_path = out_dir / "_workflow_log.md"
    log_path.write_text(log_md, encoding="utf-8")

    # 직전 실행 경로 기록
    (Path(output_root) / "_last_run.txt").write_text(str(out_dir), encoding="utf-8")

    progress("done", f"완료 — {out_dir}")

    artifact_paths = {
        "constitution": out_dir / "constitution.md",
        "service_brief": out_dir / "service_brief.md",
        "mvp_scope": out_dir / "mvp_scope.md",
        "user_flow": out_dir / "user_flow.md",
        "build_plan": out_dir / "build_plan.md",
        "qa_plan": out_dir / "qa_plan.md",
        "data_schema": out_dir / "data_schema.json",
        "state_machine": out_dir / "state_machine.md",
        "prompt_spec": out_dir / "prompt_spec.md",
        "interface_spec": out_dir / "interface_spec.md",
    }

    return PipelineResult(
        output_dir=out_dir,
        constitution_md=constitution_md,
        gate1=gate1,
        artifacts=artifacts,
        gate2=gate2,
        gate3=gate3,
        artifact_paths=artifact_paths,
        workflow_log_path=log_path,
    )