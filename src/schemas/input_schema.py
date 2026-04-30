"""사용자 입력 스키마 (기획서 4.1).

서비스 기획 정보(4종) + 실행 제약 정보(4종) = 총 8개 필드.
필수 6 / 선택 2.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ServicePlan(BaseModel):
    """서비스 기획 정보."""

    target_user: str = Field(
        ...,
        description="서비스를 사용할 핵심 사용자 집단",
        examples=["AI를 공부에 활용하지만 질문을 잘 못하는 중학생"],
    )
    problem: str = Field(
        ...,
        description="현재 사용자가 겪고 있는 문제 상황",
        examples=["막연한 질문을 입력해 원하는 답을 얻지 못하고 AI 활용 효율이 낮다."],
    )
    goal: str = Field(
        ...,
        description="서비스 목표(서비스를 통해 개선하고자 하는 결과)",
        examples=["학생의 질문 품질을 높여 AI 학습 활용 효율을 향상한다."],
    )
    solution: str | None = Field(
        default=None,
        description="구현하려는 서비스 형태 또는 솔루션 아이디어 (선택)",
        examples=["질문 코칭 챗봇 MVP"],
    )


class ExecutionConstraints(BaseModel):
    """실행 제약 정보."""

    deadline: date = Field(
        ...,
        description="결과물을 완성해야 하는 날짜",
        examples=["2026-05-01"],
    )
    team_size: int = Field(
        ...,
        ge=1,
        description="실제 참여 인원 수",
        examples=[3],
    )
    team_capability: str = Field(
        ...,
        description="팀의 현재 보유 역량",
        examples=["교육 기획 강점 / 프론트 기초 가능 / 개발 이해도 중간"],
    )
    existing_assets: str | None = Field(
        default=None,
        description="이미 보유한 문서·기능 정의·코드 등 자산 (선택). LLM API 제약도 여기에 포함 (예: Upstage Solar-pro2 사용)",
        examples=["기획 문서 초안 있음 / 기능 정의 문서 있음 / 코드베이스 없음 / Upstage Solar-pro2 사용"],
    )


class HarnessInput(BaseModel):
    """하네스에 전달되는 최상위 입력. inputs/*.json 의 구조와 일치한다."""

    service: ServicePlan
    constraints: ExecutionConstraints

    def to_global_context(self, today: date | None = None) -> str:
        """프롬프트에 주입할 [Global] Input 블록 텍스트를 생성한다.

        모든 에이전트가 산출물 작성 시 이 블록을 참조하여 사용자 원 요구사항을 보존한다.

        설계 결정 (deadline 환각 차단):
        - LLM 의 산술 약점을 우회하기 위해 (오늘, deadline, 남은 일수) 를 미리 계산해 박는다.
        - LLM 은 직접 산술하지 않고 명시된 "남은 일수" 숫자만 그대로 활용하면 됨.

        Args:
            today: 오늘 날짜. None 이면 date.today() 사용 (테스트 재현성 위해 인자화).
        """
        from datetime import date as _date
        today = today or _date.today()
        days_remaining = (self.constraints.deadline - today).days

        s = self.service
        c = self.constraints
        lines = [
            "[서비스 기획 정보]",
            f"- 타깃 유저(target_user): {s.target_user}",
            f"- 문제 상황(problem): {s.problem}",
            f"- 서비스 목표(goal): {s.goal}",
            f"- 솔루션 아이디어(solution): {s.solution or '(미입력)'}",
            "",
            "[실행 제약 정보]",
            f"- 마감 기한(deadline): {c.deadline.isoformat()}",
            f"- 오늘 날짜(today): {today.isoformat()}",
            f"- **[중요] 남은 일수(days_remaining): {days_remaining}일** "
            "(이 숫자를 기준으로 모든 일정·범위를 결정한다. "
            "산술은 이미 끝났으니 그대로 사용할 것.)",
            f"- 팀 인원(team_size): {c.team_size}명",
            f"- 팀 역량(team_capability): {c.team_capability}",
            f"- 보유 자산(existing_assets): {c.existing_assets or '(없음)'}",
        ]
        return "\n".join(lines)
