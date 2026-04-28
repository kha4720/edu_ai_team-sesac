"""Upstage Solar API 호출 래퍼.

Solar는 OpenAI 호환 API를 제공하므로, openai SDK에 base_url만 변경해서 사용한다.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

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


def _log_call(label: str, model: str, elapsed: float, in_tokens: int | None, out_tokens: int | None) -> None:
    """간단한 호출 로그. 모델/소요시간/토큰 사용량을 한 줄로."""
    parts = [f"[Solar] {label} | model={model} | {elapsed:.1f}s"]
    if in_tokens is not None and out_tokens is not None:
        parts.append(f"tok in/out={in_tokens}/{out_tokens}")
    print(" | ".join(parts))


def chat(
    system: str,
    user: str,
    *,
    label: str = "chat",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """단발성 chat 호출. system + user 메시지를 받아 응답 텍스트를 반환한다."""
    cfg = _load_config()
    client = _client(cfg)
    used_model = model or cfg.model
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=used_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.perf_counter() - started
    usage = response.usage
    _log_call(
        label,
        used_model,
        elapsed,
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
    )
    return response.choices[0].message.content or ""


def chat_json(
    system: str,
    user: str,
    *,
    label: str = "chat_json",
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """JSON 객체로만 응답하도록 강제하고, 파싱된 dict 를 반환한다.

    프롬프트 측에서도 "JSON 으로만 답하라"고 명시할 것 (이중 안전망).
    """
    cfg = _load_config()
    client = _client(cfg)
    used_model = model or cfg.model
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=used_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    elapsed = time.perf_counter() - started
    raw = response.choices[0].message.content or "{}"
    usage = response.usage
    _log_call(
        label,
        used_model,
        elapsed,
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"JSON 응답 파싱 실패 ({label}): {e}\n--- raw ---\n{raw}"
        ) from e
