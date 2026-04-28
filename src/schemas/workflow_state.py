"""Workflow State 스키마 (기획서 4.2).

하네스의 실행 상태를 저장한다. JSON 으로 직렬화해 파일에 기록.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# === 4.2.2 current_step / current_task ===

CurrentStep = Literal[1, 2, 3, 4]
"""1: 입력 / 2: 헌법 / 3: 기획문서 5종 / 4: 구현명세 4종"""


class CurrentTask(str, Enum):
    """기획서 4.2.2 표 그대로."""

    USER_INPUT_SETUP = "user_input_setup"
    CONSTITUTION_WRITE = "constitution_write"

    # Step 3 — 기획 문서 5종 (순차)
    SERVICE_BRIEF_WRITE = "service_brief_write"
    MVP_SCOPE_WRITE = "mvp_scope_write"
    USER_FLOW_WRITE = "user_flow_write"
    BUILD_PLAN_WRITE = "build_plan_write"
    QA_PLAN_WRITE = "qa_plan_write"

    # Step 4 — 구현 명세 4종
    DATA_SCHEMA_WRITE = "data_schema_write"
    STATE_MACHINE_WRITE = "state_machine_write"
    PROMPT_SPEC_WRITE = "prompt_spec_write"
    INTERFACE_SPEC_WRITE = "interface_spec_write"


# === 4.2.4 task_status / gate_result ===


class TaskStatus(str, Enum):
    PENDING = "pending"
    WORKING = "working"
    COMPLETED = "completed"
    REWORKING = "reworking"


class GateResult(str, Enum):
    PENDING = "pending"
    PASS_ = "pass"  # 'pass' 는 파이썬 예약어이므로 변수명만 PASS_
    FAIL = "fail"
    CONDITIONAL_PASS = "conditional_pass"


CurrentGate = Literal[1, 2, 3] | None
"""1: 헌법 / 2: 기획문서 5종 / 3: 구현명세 4종 / None: 검증 단계 아님"""


class OverallStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# === 4.2.1 핵심 필드 정의 ===


class WorkflowState(BaseModel):
    """하네스의 실행 상태 전체."""

    # 현재 위치
    current_step: CurrentStep = 1
    current_task: CurrentTask = CurrentTask.USER_INPUT_SETUP
    current_gate: CurrentGate = None

    # 상태값
    task_status: TaskStatus = TaskStatus.PENDING
    gate_result: GateResult = GateResult.PENDING
    overall_status: OverallStatus = OverallStatus.INITIALIZED

    # 책임자
    owner: str | None = Field(default=None, description="현재 작업 책임 Agent 이름")

    # 재시도 / 메모
    retry_count: int = Field(default=0, ge=0, le=2, description="동일 Gate 재검토 횟수 (최대 1회)")
    feedback_target: str | None = Field(default=None, description="수정 대상 Agent")
    feedback_memo: str | None = Field(default=None, description="수정 요청 내용")
    risk_memo: str | None = Field(default=None, description="조건부 통과 시 남기는 리스크")

    # 메타
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 산출물 경로 추적
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="이미 생성된 산출물의 파일 경로 매핑. key=artifact_id, value=상대경로",
    )

    def touch(self) -> None:
        """updated_at 을 갱신한다."""
        self.updated_at = datetime.now()
