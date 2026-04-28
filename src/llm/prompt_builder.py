"""에이전트 공용 프롬프트 빌더.

모든 산출물 작성 프롬프트는 다음 공통 골격을 따른다 (기획서 3.4.1 컨텍스트 참조 원칙):

    [Global Context]   ← 단계별로 다름 (아래 주의 참고)
    [Primary Inputs]   ← 직전 단계의 핵심 근거 문서
    [Secondary Inputs] ← 보조 참고 자료 (선택)
    [작성 지시]         ← 이번 산출물의 구체 요구사항

> **주의:** Global Context의 구성은 단계마다 다르다.
>   - Step 2~3 (헌법, 기획문서 5종): harness_input + constitution
>   - Step 4   (구현명세 4종):       constitution 만 (사용자 input 제외)
> 이 분기 책임은 **각 에이전트(또는 호출자)** 에게 있다. 빌더는 받은 블록을
> 그대로 조립할 뿐, 어떤 블록을 넣을지 결정하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTION_DIVIDER = "\n\n" + "=" * 60 + "\n"


@dataclass
class PromptContext:
    """프롬프트에 포함할 컨텍스트 묶음.

    각 dict 의 key 는 사람이 읽기 좋은 라벨 (예: "사용자 입력", "헌법"),
    value 는 해당 블록의 마크다운/텍스트 내용.
    """

    global_blocks: dict[str, str] = field(default_factory=dict)
    primary_blocks: dict[str, str] = field(default_factory=dict)
    secondary_blocks: dict[str, str] = field(default_factory=dict)


def _format_block(label: str, content: str) -> str:
    return f"### {label}\n\n{content.strip()}\n"


def _format_group(group_name: str, blocks: dict[str, str]) -> str:
    if not blocks:
        return ""
    body_parts = [_format_block(label, content) for label, content in blocks.items()]
    return f"## [{group_name}]\n\n" + "\n".join(body_parts)


def build_user_prompt(
    *,
    context: PromptContext,
    instruction: str,
    output_format_hint: str | None = None,
) -> str:
    """User 메시지 본문을 조립한다.

    Args:
        context: Global / Primary / Secondary 블록 (호출자가 단계별로 알맞게 채워서 전달).
        instruction: 이번 호출에서 LLM 에게 요구하는 작업 지시.
        output_format_hint: 출력 형식에 대한 추가 지시 (예: "마크다운 본문만 출력하라").
    """
    parts = []
    g = _format_group("Global Context", context.global_blocks)
    if g:
        parts.append(g)
    p = _format_group("Primary Inputs", context.primary_blocks)
    if p:
        parts.append(p)
    s = _format_group("Secondary Inputs", context.secondary_blocks)
    if s:
        parts.append(s)

    parts.append(f"## [작성 지시]\n\n{instruction.strip()}")
    if output_format_hint:
        parts.append(f"## [출력 형식]\n\n{output_format_hint.strip()}")
    return SECTION_DIVIDER.join(parts)
