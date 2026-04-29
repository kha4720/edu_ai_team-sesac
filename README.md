# edu_ai_team (SeSAC)

SeSAC AI 팀 코드 공유 레포지토리입니다.

---

## 프로젝트 구조

이 팀 프로젝트는 두 개의 트랙으로 구성됩니다.

### [Track 1] Edu Design Harness — 기획 자동화

교육 서비스 기획자가 아이디어와 실행 제약을 입력하면, 5개의 LLM 에이전트(Orchestrator / Edu / PM / Tech / Prompt)가 협업해 **헌법 1종 + 기획문서 5종 + 구현명세 4종**을 자동 생성하는 멀티에이전트 하네스.

**기술 스택**: Python 3.11+ / Upstage Solar API / Pydantic v2 / LangGraph / uv

**담당 브랜치**: `hyeona`

---

### [Track 2] 구현 자동화

Track 1에서 산출된 구현명세서 4종을 입력으로 받아, 실제 서비스 코드를 자동 생성하는 파이프라인.

*(상세 내용은 해당 담당자 브랜치 참고)*

---

## 브랜치 구조

```
main   ← 안정 버전 (직접 push 금지)
 └── dev   ← 통합 브랜치
      └── hyeona   ← Track 1 담당 (팀장)
      └── (이름)   ← Track 2 담당 팀원 브랜치
```

---

## 팀원 브랜치 세팅 방법

### 1. 레포지토리 클론

```bash
git clone https://github.com/kha4720/edu_ai_team-sesac.git
cd edu_ai_team-sesac
```

### 2. 내 이름 브랜치로 이동

```bash
# 처음 세팅하는 경우 (dev 기준으로 생성)
git checkout -b 이름 origin/dev

# 이미 생성된 브랜치가 있는 경우
git checkout 이름
```

### 3. 작업 후 내 브랜치에 push

```bash
git add .
git commit -m "작업 내용 요약"
git push origin 이름
```

> **주의**: `main` / `dev` 브랜치에는 직접 push하지 마세요. 팀장에게 요청해주세요.

---

## 환경 설정 (Track 1)

```bash
# 의존성 설치 (uv 필요)
uv sync

# .env 파일 생성
cp .env.example .env
# UPSTAGE_API_KEY 값 입력
```