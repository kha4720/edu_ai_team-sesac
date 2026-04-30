"""Streamlit UI — 교육 서비스 기획 문서 하네스.

실행:
    uv run streamlit run app.py
"""

from __future__ import annotations

import re
from datetime import date

import streamlit as st

from src.runner import PipelineResult, run_pipeline
from src.schemas.input_schema import (
    ExecutionConstraints,
    HarnessInput,
    ServicePlan,
)


st.set_page_config(
    page_title="AI 기반 교육 서비스 기획 하네스",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📚 AI 기반 교육 서비스 기획 하네스")
st.caption(
    "LLM API를 활용하는 AI 교육 서비스 기획에 특화된 하네스. "
    "4개 LLM 에이전트(Edu / PM / Tech / Prompt) + Team Lead 가 "
    "협업하여 서비스 원칙서 + 기획문서 5종 + 구현 명세서 4종을 자동 생성합니다."
)


# ============================================================
# 입력 영역 — 메인 상단 2단
# ============================================================

INPUT_HEIGHT = 68  # Streamlit text_area 최저 높이

col_service, col_constraint = st.columns(2, gap="large")

with col_service:
    st.subheader("🎯 서비스 기획 정보")
    target_user = st.text_area(
        "타깃 유저",
        value="AI를 공부에 활용하지만 질문을 잘 못하는 중학생",
        help="서비스를 사용할 핵심 사용자 집단",
        height=INPUT_HEIGHT,
    )
    problem = st.text_area(
        "문제 상황",
        value="막연한 질문을 입력해 원하는 답을 얻지 못하고 AI 활용 효율이 낮다.",
        help="현재 사용자가 겪고 있는 문제 상황",
        height=INPUT_HEIGHT,
    )
    goal = st.text_area(
        "서비스 목표",
        value="학생의 질문 품질을 높여 AI 학습 활용 효율을 향상한다.",
        help="서비스를 통해 개선하고자 하는 결과",
        height=INPUT_HEIGHT,
    )
    solution = st.text_area(
        "솔루션 아이디어 (선택)",
        value="질문 코칭 챗봇 MVP",
        help="구현하려는 서비스 형태 또는 솔루션 아이디어",
        height=INPUT_HEIGHT,
    )

with col_constraint:
    st.subheader("⚙️ 실행 제약 정보")
    sub_a, sub_b = st.columns(2)
    with sub_a:
        deadline = st.date_input(
            "마감 기한",
            value=date(2026, 5, 1),
            help="결과물을 완성해야 하는 날짜",
        )
    with sub_b:
        team_size = st.number_input(
            "팀 인원",
            min_value=1,
            max_value=20,
            value=3,
            help="실제 참여 인원 수",
        )

    team_capability = st.text_area(
        "팀 가용 역량",
        value="교육 기획 강점 / 프론트 기초 가능 / 개발 이해도 중간",
        help="팀의 현재 보유 역량",
        height=INPUT_HEIGHT,
    )
    existing_assets = st.text_area(
        "보유 자산 (선택)",
        value="기획 문서 초안 있음 / 기능 정의 문서 있음 / 코드베이스 없음 / Upstage Solar-pro2 사용",
        help="이미 보유한 문서·기능 정의·코드 등 자산. LLM API 제약도 여기에 포함",
        height=INPUT_HEIGHT,
    )
    project_slug = st.text_input(
        "프로젝트 식별자 (저장 폴더명)",
        value="question_coach",
        help="출력 폴더 prefix. 영문/숫자/_ 만 사용 권장",
    )


st.markdown("---")
run_button = st.button("🚀 하네스 실행", type="primary", use_container_width=True)


# ============================================================
# 산출물 자리 — placeholder 미리 표시 (실행 전에도 보임)
# ============================================================


# 실행 결과를 rerun 이후에도 유지 (download_button 클릭 시 rerun 대응)
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

# 진행 상황 박스 자리
progress_slot = st.empty()

# 산출물 탭 정의 — (artifact_id, 탭 라벨, 작성자)
ARTIFACT_VIEW = [
    ("constitution",   "📜 서비스 원칙서",    "Edu Agent"),
    ("gate1_log",      "🛡️ Gate 1",          "Team Lead"),
    ("service_brief",  "📝 Service Brief",   "PM Agent"),
    ("mvp_scope",      "🎯 MVP Scope",       "PM Agent"),
    ("user_flow",      "🧭 User Flow",       "PM Agent"),
    ("build_plan",     "🔧 Build Plan",      "Tech Agent"),
    ("qa_plan",        "🧪 QA Plan",         "PM Agent"),
    ("gate2_log",      "🛡️ Gate 2",          "Team Lead + Edu + Tech"),
    ("data_schema",    "📊 Data Schema",     "PM Agent"),
    ("state_machine",  "🔀 State Machine",   "PM Agent"),
    ("prompt_spec",    "💬 Prompt Spec",     "Prompt Agent"),
    ("interface_spec", "🔗 Interface Spec",  "PM Agent"),
    ("gate3_log",      "🛡️ Gate 3",          "Team Lead"),
]

# 탭 8개 생성 + 각 탭 안에 placeholder
tabs = st.tabs([label for _, label, _ in ARTIFACT_VIEW])
artifact_slots: dict[str, st.delta_generator.DeltaGenerator] = {}
for tab, (artifact_id, label, owner) in zip(tabs, ARTIFACT_VIEW):
    with tab:
        st.caption(f"작성자: **{owner}**")
        artifact_slots[artifact_id] = st.empty()
        artifact_slots[artifact_id].info("⏳ 실행 후 여기에 결과가 표시됩니다.")

# rerun 시 (download_button 클릭 등) 이전 결과 복원
_stored = st.session_state.pipeline_result
if _stored is not None:
    for _aid, _path in _stored.artifact_paths.items():
        _slot = artifact_slots.get(_aid)
        if _slot and _path.exists():
            _slot.markdown(_path.read_text(encoding="utf-8"), unsafe_allow_html=True)
    for _key, _fn in [
        ("gate1_log", _stored.gate1.to_log_markdown),
        ("gate2_log", _stored.gate2.to_log_markdown),
        ("gate3_log", _stored.gate3.to_log_markdown),
    ]:
        _slot = artifact_slots.get(_key)
        if _slot:
            _slot.markdown(_fn(), unsafe_allow_html=True)


# ============================================================
# 실행 / 결과
# ============================================================


def _slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip()) or "harness"
    return text[:40]


def _build_input() -> HarnessInput:
    return HarnessInput(
        service=ServicePlan(
            target_user=target_user,
            problem=problem,
            goal=goal,
            solution=solution.strip() or None,
        ),
        constraints=ExecutionConstraints(
            deadline=deadline,
            team_size=int(team_size),
            team_capability=team_capability,
            existing_assets=existing_assets.strip() or None,
        ),
    )


if run_button:
    try:
        harness_input = _build_input()
    except Exception as e:
        st.error(f"입력값 검증 실패: {e}")
        st.stop()

    progress_box = progress_slot.status("하네스 실행 중...", expanded=True)

    def on_progress(stage: str, message: str) -> None:
        progress_box.write(f"**[{stage}]** {message}")

    def on_artifact(artifact_id: str, markdown: str) -> None:
        slot = artifact_slots.get(artifact_id)
        if slot is None:
            return
        slot.markdown(markdown, unsafe_allow_html=True)

    try:
        result: PipelineResult = run_pipeline(
            harness_input,
            project_slug=_slugify(project_slug),
            on_progress=on_progress,
            on_artifact=on_artifact,
        )
        st.session_state.pipeline_result = result
        progress_box.update(label="완료 ✅", state="complete")
    except Exception as e:
        progress_box.update(label="실패 ❌", state="error")
        st.error(f"실행 중 오류: {type(e).__name__}: {e}")
        st.stop()

if not run_button and st.session_state.pipeline_result is None:
    progress_slot.info(
        "위 입력값을 확인하고 **🚀 하네스 실행** 버튼을 누르세요. "
        "처음 실행 시 약 2–3분 소요됩니다 (LLM 호출 약 17–20회). "
        "산출물이 한 단계씩 완성될 때마다 아래 박스에 즉시 표시됩니다."
    )

# Gate 결과 metric + 다운로드 — session_state 기준으로 렌더링 (rerun 후에도 유지)
_result = st.session_state.pipeline_result
if _result is not None:
    st.success(f"✅ 완료 — `{_result.output_dir}`")
    g1 = _result.gate1.final_verdict.value
    g2 = _result.gate2.final_verdict.value
    g3 = _result.gate3.final_verdict.value
    cols = st.columns(3)
    cols[0].metric("Gate 1 (원칙서 검증)", g1)
    cols[1].metric("Gate 2 (기획문서 5종)", g2)
    cols[2].metric("Gate 3 (구현 명세서 4종)", g3)

    if _result.step_timings:
        _STEP_LABELS = {
            "constitution":   "서비스 원칙서 (Edu Agent)",
            "gate1":          "Gate 1",
            "service_brief":  "Service Brief (PM)",
            "mvp_scope":      "MVP Scope (PM)",
            "user_flow":      "User Flow (PM)",
            "build_plan":     "Build Plan (Tech)",
            "qa_plan":        "QA Plan (PM)",
            "gate2":          "Gate 2",
            "data_schema":    "Data Schema (PM)",
            "state_machine":  "State Machine (PM) ┐병렬",
            "prompt_spec":    "Prompt Spec (Prompt) ┘병렬",
            "interface_spec": "Interface Spec (PM)",
            "gate3":          "Gate 3",
        }
        st.markdown("### ⏱️ 단계별 실행 시간")
        timing_rows = [
            {"단계": _STEP_LABELS.get(k, k), "소요 시간": f"{v:.1f}s"}
            for k, v in _result.step_timings.items()
        ]
        st.table(timing_rows)
        st.caption(f"총 소요 시간: **{_result.total_elapsed:.1f}초**")

    st.markdown("### 📥 산출물 다운로드")
    dl_cols = st.columns(5)
    download_specs = [
        ("constitution",  "constitution.md",  "text/markdown"),
        ("service_brief", "service_brief.md", "text/markdown"),
        ("mvp_scope",     "mvp_scope.md",     "text/markdown"),
        ("user_flow",     "user_flow.md",     "text/markdown"),
        ("build_plan",    "build_plan.md",    "text/markdown"),
    ]
    for col, (artifact_id, fname, mime) in zip(dl_cols, download_specs):
        path = _result.artifact_paths[artifact_id]
        col.download_button(fname, data=path.read_text(encoding="utf-8"), file_name=fname, mime=mime)

    dl_cols2 = st.columns(5)
    download_specs2 = [
        ("qa_plan",        "qa_plan.md",        "text/markdown"),
        ("data_schema",    "data_schema.json",  "application/json"),
        ("state_machine",  "state_machine.md",  "text/markdown"),
        ("prompt_spec",    "prompt_spec.md",    "text/markdown"),
        ("interface_spec", "interface_spec.md", "text/markdown"),
    ]
    for col, (artifact_id, fname, mime) in zip(dl_cols2, download_specs2):
        path = _result.artifact_paths[artifact_id]
        col.download_button(fname, data=path.read_text(encoding="utf-8"), file_name=fname, mime=mime)

    if _result.workflow_log_path and _result.workflow_log_path.exists():
        st.download_button(
            "📊 워크플로우 로그 (전체)",
            data=_result.workflow_log_path.read_text(encoding="utf-8"),
            file_name="_workflow_log.md",
            mime="text/markdown",
        )