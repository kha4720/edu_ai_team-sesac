"""Solar API 연결 확인용 스모크 테스트.

사용:
    uv run python -m src.llm._test_solar

목적:
- .env 의 UPSTAGE_API_KEY 가 잘 읽히는지
- Solar API 가 살아있고 응답을 주는지
- src.llm.solar.chat() 함수가 정상 동작하는지
한 번에 확인하기 위한 안전망.
"""

from src.llm.solar import chat


def main() -> None:
    print("[Solar 연결 테스트] 호출 중...")
    try:
        reply = chat(
            system="너는 친절한 한국어 도우미야. 반드시 한국어로 짧게 답해.",
            user="에듀하네스 연결 테스트 중이야. '연결 성공'이라고만 답해줘.",
        )
    except Exception as e:
        print(f"[실패] {type(e).__name__}: {e}")
        raise

    print(f"[응답] {reply}")
    print("[OK] Solar API 연결 정상")


if __name__ == "__main__":
    main()
