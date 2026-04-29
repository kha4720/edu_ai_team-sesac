"""Artifact Schema (기획서 4.3 / 5.1).

산출물 10종(헌법 1 + 기획 5 + 구현명세 4)의 메타정보를 코드로 정의.
Team Lead 가 "지금 만들 문서가 뭐고, 의존성이 채워졌는지" 판단하는 기준이 된다.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Category(str, Enum):
    CONSTITUTION = "constitution"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"


class OwnerAgent(str, Enum):
    EDU = "edu_agent"
    PM = "pm_agent"
    TECH = "tech_agent"
    PROMPT = "prompt_agent"


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class ArtifactInputs(BaseModel):
    """주요 Input 분류 (Global / Primary / Secondary)."""

    global_: list[str] = Field(default_factory=list, alias="global")
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ArtifactSpec(BaseModel):
    """단일 산출물의 메타정보."""

    artifact_id: str
    file_name: str
    stage: Literal[2, 3, 4]
    category: Category
    owner_agent: OwnerAgent
    definition: str
    inputs: ArtifactInputs
    dependencies: list[str] = Field(
        default_factory=list,
        description="이 산출물이 만들어지기 전에 완료되어야 할 artifact_id 목록",
    )
    required_sections: list[str] = Field(
        default_factory=list,
        description="필수 목차 (검증 시 누락 여부 확인)",
    )
    writing_rules: str = ""
    quality_criteria: list[str] = Field(default_factory=list)
    output_format: OutputFormat = OutputFormat.MARKDOWN


# ========================================================================
# 산출물 10종 정의 (기획서 5.1.1 / 5.2 / 5.3 / 5.4 표를 그대로 옮김)
# ========================================================================


CONSTITUTION = ArtifactSpec(
    artifact_id="constitution",
    file_name="constitution.md",
    stage=2,
    category=Category.CONSTITUTION,
    owner_agent=OwnerAgent.EDU,
    definition="하네스의 최상위 교육 설계 기준서. 모든 후속 문서의 판단 기준.",
    inputs=ArtifactInputs(**{"global": ["harness_input"]}),
    dependencies=[],
    required_sections=[
        "교육공학적 문제 재정의",
        "교수 기법 탐색",
        "MVP 교수 기법 선정",
        "서비스 전체 설계 원칙",
        "학습 목표",
        "평가 루브릭",
        "루브릭 기반 서비스 플로우 원칙",
    ],
    writing_rules=(
        "①~③은 설계 근거(사용자 입력 → 학습 결핍 정의), "
        "④~⑦은 실행 기준(헌법). ④~⑦이 후속 문서의 평가 기준점이 된다."
    ),
    quality_criteria=[
        "완전성: ④~⑦ 핵심 항목이 모두 작성되었는가?",
        "상위 기준 일관성: ⑤~⑦이 ④ 설계 원칙과 충돌하지 않는가?",
        "내부 연계성: ⑤~⑦이 논리적으로 연결되어 있는가?",
        "근거 타당성: ①~③ 판단이 ④에 적절히 반영되었는가?",
    ],
)


SERVICE_BRIEF = ArtifactSpec(
    artifact_id="service_brief",
    file_name="service_brief.md",
    stage=3,
    category=Category.PLANNING,
    owner_agent=OwnerAgent.PM,
    definition="서비스의 핵심 개념을 빠르게 이해시키는 1장짜리 요약 문서.",
    inputs=ArtifactInputs(**{"global": ["harness_input", "constitution"]}),
    dependencies=["constitution"],
    required_sections=[
        "타겟 사용자",
        "핵심 문제",
        "핵심 가치",
        "해결 방식",
        "주요 기능 영역",
        "서비스명",
        "한 줄 설명",
    ],
    writing_rules=(
        "한눈에 이해되도록 간결하게. 핵심 가치는 헌법 ⑤(학습 목표)와 연결, "
        "해결 방식은 헌법 ④(설계 원칙)이 드러나야 한다."
    ),
    quality_criteria=[
        "핵심 문제가 타겟 사용자의 불편과 원인을 함께 반영하는가?",
        "MVP 핵심 기능만 포함되어 있는가?",
    ],
)


MVP_SCOPE = ArtifactSpec(
    artifact_id="mvp_scope",
    file_name="mvp_scope.md",
    stage=3,
    category=Category.PLANNING,
    owner_agent=OwnerAgent.PM,
    definition="이번에 구현할 서비스 필수 범위(MVP)를 정하는 문서.",
    inputs=ArtifactInputs(
        **{"global": ["harness_input", "constitution"]},
        primary=["service_brief"],
    ),
    dependencies=["service_brief"],
    required_sections=[
        "선정 기준",
        "필수 기능",
        "제외 기능",
        "기능 개발 순서",
        "MVP 구현 수준",
    ],
    writing_rules="실행 제약(기한·인력·기술 수준) 우선 반영. 제외 기능은 명확히 기재.",
    quality_criteria=[
        "Service Brief 의 핵심 문제·핵심 가치가 반영되었는가?",
        "사용자 입력의 실행 제약이 반영되었는가?",
    ],
)


USER_FLOW = ArtifactSpec(
    artifact_id="user_flow",
    file_name="user_flow.md",
    stage=3,
    category=Category.PLANNING,
    owner_agent=OwnerAgent.PM,
    definition="사용자가 MVP 필수 기능을 경험하는 흐름을 정리한 문서.",
    inputs=ArtifactInputs(
        **{"global": ["harness_input", "constitution"]},
        primary=["mvp_scope"],
    ),
    dependencies=["mvp_scope"],
    required_sections=[
        "핵심 화면",
        "사용자 흐름 정리",
        "화면 전환 조건",
        "반복 사용 흐름",
        "종료 / 재시도 흐름",
    ],
    writing_rules="MVP Scope 의 필수 기능을 빠르게 경험하도록 화면 흐름을 단순하게 설계.",
    quality_criteria=[
        "MVP Scope 의 필수 기능이 모두 흐름에 포함되는가?",
        "헌법 ⑦(루브릭 기반 서비스 플로우)의 화면 전환·피드백 구조를 반영하는가?",
    ],
)


BUILD_PLAN = ArtifactSpec(
    artifact_id="build_plan",
    file_name="build_plan.md",
    stage=3,
    category=Category.PLANNING,
    owner_agent=OwnerAgent.TECH,
    definition="MVP 기능을 실제로 구현하기 위한 최소 개발 계획 문서.",
    inputs=ArtifactInputs(
        **{"global": ["harness_input", "constitution"]},
        primary=["mvp_scope", "user_flow"],
    ),
    dependencies=["mvp_scope", "user_flow"],
    required_sections=[
        "구현 모듈",
        "필요 API / AI 기능",
        "기술 방식",
        "구현 순서",
        "담당 역할",
        "완료 기준",
    ],
    writing_rules="실행 제약 우선 반영. 최소 복잡도의 스택. 시연 가능 여부로 완료 판단.",
    quality_criteria=[
        "일정·인력·기술 수준 내 구현 가능한가?",
        "각 모듈이 역할/입력/출력/연결되는 User Flow 단계를 포함하는가?",
    ],
)


QA_PLAN = ArtifactSpec(
    artifact_id="qa_plan",
    file_name="qa_plan.md",
    stage=3,
    category=Category.PLANNING,
    owner_agent=OwnerAgent.PM,
    definition="MVP 기능과 사용자 흐름이 의도대로 동작하는지 검증하기 위한 품질 검증 계획.",
    inputs=ArtifactInputs(
        **{"global": ["harness_input", "constitution"]},
        primary=["mvp_scope", "user_flow", "build_plan"],
    ),
    dependencies=["mvp_scope", "user_flow", "build_plan"],
    required_sections=[
        "검증 목표",
        "테스트 항목",
        "성공 기준",
        "테스트 시나리오",
        "엣지 케이스 및 예외 처리 시나리오",
        "에러 메시지 정의",
        "개선 판단 포인트",
    ],
    writing_rules="헌법 ⑥(평가 루브릭)을 성공 기준 수립의 근거로 활용. 예외/에러 시나리오 포함.",
    quality_criteria=[
        "MVP Scope 필수 기능 동작 여부를 모두 커버하는가?",
        "예외 케이스 및 에러 시나리오가 포함되어 있는가?",
    ],
)


DATA_SCHEMA = ArtifactSpec(
    artifact_id="data_schema",
    file_name="data_schema.json",
    stage=4,
    category=Category.IMPLEMENTATION,
    owner_agent=OwnerAgent.PM,
    definition="MVP 기능 구현에 필요한 입력·출력 데이터 구조와 필드 규격.",
    inputs=ArtifactInputs(
        **{"global": ["constitution"]},
        primary=["mvp_scope", "user_flow"],
        secondary=["build_plan"],
    ),
    dependencies=["mvp_scope", "user_flow", "build_plan"],
    required_sections=["input", "output"],
    writing_rules=(
        "MVP 구현에 필요한 최소 필드만 정의. 헌법 ⑦의 시스템 판단을 mode 필드로 표현. "
        "각 필드는 type / required / description / example / source 포함."
    ),
    quality_criteria=[
        "MVP 기능에 필요한 최소 데이터를 포함하는가?",
        "필드 정의가 명확한가 (type, required, description, example)?",
    ],
    output_format=OutputFormat.JSON,
)


STATE_MACHINE = ArtifactSpec(
    artifact_id="state_machine",
    file_name="state_machine.md",
    stage=4,
    category=Category.IMPLEMENTATION,
    owner_agent=OwnerAgent.PM,
    definition="서비스의 각 상태와 상태 간 전이 조건, 예외 처리를 정의한 비즈니스 로직 문서.",
    inputs=ArtifactInputs(
        **{"global": ["constitution"]},
        primary=["user_flow", "qa_plan"],
        secondary=["build_plan", "mvp_scope"],
    ),
    dependencies=["user_flow", "qa_plan", "data_schema"],
    required_sections=[
        "상태 목록",
        "상태 전이 규칙",
        "data_schema mode 값 매핑 규칙",
        "예외 처리 및 에러 메시지",
        "data_schema mode 값 매핑",
    ],
    writing_rules=(
        "헌법 ⑦의 시스템 판단을 상태값으로 구체화. IF-THEN 구조. "
        "data_schema 의 mode 와 1:1 대응. 모든 분기(양호/미흡/예외) 명시."
    ),
    quality_criteria=[
        "헌법 ⑦의 시스템 판단 구조가 반영되었는가?",
        "data_schema mode 와 출력 필드가 일치하는가?",
    ],
)


PROMPT_SPEC = ArtifactSpec(
    artifact_id="prompt_spec",
    file_name="prompt_spec.md",
    stage=4,
    category=Category.IMPLEMENTATION,
    owner_agent=OwnerAgent.PROMPT,
    definition="헌법의 교육 설계 원칙을 LLM 이 실제로 따를 수 있는 프롬프트 언어로 번역한 문서.",
    inputs=ArtifactInputs(
        **{"global": ["constitution"]},
        primary=["constitution"],
        secondary=["mvp_scope", "user_flow", "qa_plan"],
    ),
    dependencies=["constitution", "data_schema"],
    required_sections=[
        "공통 시스템 프롬프트",
        "모드별 프롬프트",
        "Few-shot 예시 모음",
        "출력 형식 정의",
    ],
    writing_rules=(
        "④→Constraints, ⑤→Role, ⑥→판단 로직, ⑦→모드별 분기. "
        "각 모드당 Few-shot 2개 이상. 출력 필드는 data_schema 와 일치."
    ),
    quality_criteria=[
        "헌법 ④⑤⑥⑦ 내용이 누락 없이 반영되었는가?",
        "모드별 프롬프트가 분리되어 있는가?",
    ],
)


INTERFACE_SPEC = ArtifactSpec(
    artifact_id="interface_spec",
    file_name="interface_spec.md",
    stage=4,
    category=Category.IMPLEMENTATION,
    owner_agent=OwnerAgent.PM,
    definition="화면, API, 모듈 간 입출력 연결 기준을 정의한 프론트-백 계약서.",
    inputs=ArtifactInputs(
        **{"global": ["constitution"]},
        primary=["user_flow", "data_schema"],
        secondary=["build_plan", "state_machine"],
    ),
    dependencies=["user_flow", "data_schema", "state_machine"],
    required_sections=[
        "API 명세",
        "UI 인터랙션 정의",
        "모듈 간 연결 구조",
    ],
    writing_rules=(
        "User Flow 의 화면/전환을 API 요청·응답 흐름으로 변환. "
        "data_schema 필드 그대로 사용. mode 별 렌더링 규칙 명시."
    ),
    quality_criteria=[
        "data_schema 와 필드가 일치하는가?",
        "User Flow 의 화면 전환 조건이 반영되었는가?",
        "에러 처리가 포함되어 있는가?",
    ],
)


# 전체 산출물 레지스트리 (Team Lead 가 순서대로 처리)
ARTIFACT_REGISTRY: dict[str, ArtifactSpec] = {
    a.artifact_id: a
    for a in [
        CONSTITUTION,
        SERVICE_BRIEF,
        MVP_SCOPE,
        USER_FLOW,
        BUILD_PLAN,
        QA_PLAN,
        DATA_SCHEMA,
        STATE_MACHINE,
        PROMPT_SPEC,
        INTERFACE_SPEC,
    ]
}


def get_artifact(artifact_id: str) -> ArtifactSpec:
    if artifact_id not in ARTIFACT_REGISTRY:
        raise KeyError(f"Unknown artifact_id: {artifact_id}")
    return ARTIFACT_REGISTRY[artifact_id]


def artifacts_by_stage(stage: int) -> list[ArtifactSpec]:
    return [a for a in ARTIFACT_REGISTRY.values() if a.stage == stage]
