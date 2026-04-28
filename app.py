"""Streamlit 데모 UI — 교육 서비스 기획 문서 하네스.

실행:
    uv run streamlit run app.py

레이아웃:
- 메인 상단: 입력 영역을 2단(서비스 기획 정보 / 실행 제약 정보) 으로 배치 (사이드바 X).
- 입력 아래: 산출물 placeholder 7개 (헌법 + 5종 + 워크플로우 로그) 미리 펼쳐 보임.
- 실행 시 단계마다 해당 placeholder 에 결과 markdown 이 즉시 채워짐.
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
    page_title="교육 서비스 기획 문서 하네스",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📚 교육 서비스 기획 문서 하네스")
st.caption(
    "사용자 아이디어를 입력하면 5개 LLM 에이전트(Edu / PM / Tech / Prompt / Orchestrator) 가 "
    "협업하여 헌법 + 기획문서 5종을 자동 생성합니다."
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
        value="기획 문서 초안 있음 / 기능 정의 문서 있음 / 코드베이스 없음",
        help="이미 보유한 문서·기능 정의·코드 등 자산",
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


# 진행 상황 박스 자리
progress_slot = st.empty()

# 산출물 탭 정의 — (artifact_id, 탭 라벨, 작성자)
ARTIFACT_VIEW = [
    ("constitution",   "📜 헌법",          "Edu Agent"),
    ("gate1_log",      "🛡️ Gate 1",        "Orchestrator"),
    ("service_brief",  "📝 Service Brief", "PM Agent"),
    ("mvp_scope",      "🎯 MVP Scope",     "PM Agent"),
    ("user_flow",      "🧭 User Flow",     "PM Agent"),
    ("build_plan",     "🔧 Build Plan",    "Tech Agent"),
    ("qa_plan",        "🧪 QA Plan",       "PM Agent"),
    ("gate2_log",      "🛡️ Gate 2",        "Orchestrator + Edu + Tech"),
]

# 탭 8개 생성 + 각 탭 안에 placeholder
tabs = st.tabs([label for _, label, _ in ARTIFACT_VIEW])
artifact_slots: dict[str, st.delta_generator.DeltaGenerator] = {}
for tab, (artifact_id, label, owner) in zip(tabs, ARTIFACT_VIEW):
    with tab:
        st.caption(f"작성자: **{owner}**")
        artifact_slots[artifact_id] = st.empty()
        artifact_slots[artifact_id].info("⏳ 실행 후 여기에 결과가 표시됩니다.")


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
        slot.markdown(markdown)

    try:
        result: PipelineResult = run_pipeline(
            harness_input,
            project_slug=_slugify(project_slug),
            on_progress=on_progress,
            on_artifact=on_artifact,
        )
        progress_box.update(label="완료 ✅", state="complete")
    except Exception as e:
        progress_box.update(label="실패 ❌", state="error")
        st.error(f"실행 중 오류: {type(e).__name__}: {e}")
        st.stop()

    # 완료 후 Gate 결과 metric + 다운로드 버튼 추가
    st.success(f"✅ 완료 — `{result.output_dir}`")
    g1 = result.gate1.final_verdict.value
    g2 = result.gate2.final_verdict.value
    cols = st.columns(2)
    cols[0].metric("Gate 1 (헌법 검증)", g1)
    cols[1].metric("Gate 2 (기획문서 5종 다중 검증)", g2)

    # 다운로드 버튼 묶음
    st.markdown("### 📥 산출물 다운로드")
    dl_cols = st.columns(6)
    download_specs = [
        ("constitution", "constitution.md"),
        ("service_brief", "service_brief.md"),
        ("mvp_scope", "mvp_scope.md"),
        ("user_flow", "user_flow.md"),
        ("build_plan", "build_plan.md"),
        ("qa_plan", "qa_plan.md"),
    ]
    for col, (artifact_id, fname) in zip(dl_cols, download_specs):
        path = result.artifact_paths[artifact_id]
        text = path.read_text(encoding="utf-8")
        col.download_button(fname, data=text, file_name=fname, mime="text/markdown")

    if result.workflow_log_path and result.workflow_log_path.exists():
        st.download_button(
            "📊 워크플로우 로그 (전체)",
            data=result.workflow_log_path.read_text(encoding="utf-8"),
            file_name="_workflow_log.md",
            mime="text/markdown",
        )
else:
    progress_slot.info(
        "위 입력값을 확인하고 **🚀 하네스 실행** 버튼을 누르세요. "
        "처음 실행 시 약 1~2분 소요됩니다 (LLM 호출 약 12~15회). "
        "산출물이 한 단계씩 완성될 때마다 아래 박스에 즉시 표시됩니다."
    )