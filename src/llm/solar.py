"""Upstage Solar API 호출 래퍼.

Solar는 OpenAI 호환 API를 제공하므로, openai SDK에 base_url만 변경해서 사용한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SOLAR_BASE_URL = "https://api.upstage.ai/v1"
DEFAULT_MODEL = os.getenv("UPSTAGE_MODEL", "solar-pro2")


@dataclass
class SolarConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = SOLAR_BASE_URL


def _load_config() -> SolarConfig:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "UPSTAGE_API_KEY 가 설정되지 않았습니다. "
            "프로젝트 루트의 .env 파일에 키를 넣어주세요."
        )
    return SolarConfig(api_key=api_key)


def _client(config: SolarConfig | None = None) -> OpenAI:
    cfg = config or _load_config()
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)


def chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """단발성 chat 호출. system + user 메시지를 받아 응답 텍스트를 반환한다."""
    cfg = _load_config()
    client = _client(cfg)
    response = client.chat.completions.create(
        model=model or cfg.model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
