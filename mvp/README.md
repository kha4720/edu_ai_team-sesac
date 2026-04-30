# Question Coach MVP

기획 문서 기반 구현 데모. 하네스 산출물(question_coach_20260430_112840)을 바탕으로 실제 동작하는 프로토타입을 구현합니다.

## 프로젝트 구조

```
mvp/
├── README.md                    # 이 파일
├── docs/                        # 기획 문서 (참조용)
│   ├── build_plan.md
│   ├── user_flow.md
│   ├── state_machine.md
│   ├── interface_spec.md
│   └── data_schema.json
├── public/                      # 정적 파일
│   └── index.html               # 메인 화면
├── src/
│   ├── app.js                   # 애플리케이션 진입점
│   ├── state-machine.js         # 상태 머신 로직
│   ├── ui-manager.js            # UI 렌더링
│   ├── llm-service.js           # LLM API 호출
│   └── session-manager.js       # 세션 관리
└── config.example.js            # 설정 예시 (OpenAI API 키 필요)
```

## 실행 방법

### 1. 사전 준비

- Node.js v14+ 설치
- Upstage API 키 (프로젝트 루트 `.env` 파일에 설정됨)

### 2. 의존성 설치

```bash
cd mvp
npm install
```

### 3. 서버 실행

```bash
npm start
# 또는
node server.js
```

### 4. 브라우저 접속

```
http://localhost:3000
```

**서버 로그:**
```
🚀 Question Coach MVP Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 로컬 주소: http://localhost:3000
🎯 API 엔드포인트:
   POST /api/generate-question   - 질문 생성
   POST /api/evaluate-purpose    - 목적 평가
```

## 기획 문서 참조

모든 구현은 `docs/` 폴더의 다음 문서를 기반으로 합니다:

| 문서 | 역할 |
|------|------|
| build_plan.md | 기술 아키텍처 (Backend 없음, Fetch API 다이렉트) |
| user_flow.md | 화면 6단계 흐름 |
| state_machine.md | 상태 전이 로직 |
| interface_spec.md | API 인터페이스 (2개) |
| data_schema.json | 입출력 데이터 스키마 |

## Build Plan과 MVP 구현의 차이

**Build Plan (기획 문서)**
- Backend 없음 (프론트엔드만)
- 마감 1일 내 완성 가능한 현실적 범위 결정

**MVP 구현 (이 프로토타입)**
- Express.js Backend 추가
- 실제 시연을 위한 인간 판단 적용
  - API 키 보안 요구사항 (브라우저에서 .env 직접 접근 불가)
  - 중앙화된 에러 처리 및 타임아웃 관리

→ 마감이 없는 검증용 MVP이므로 기획 문서의 원칙을 유지하면서도 시연 가능한 형태로 개선

## 핵심 기능

- ✅ 주제 선정 → 5W1H 입력 → 질문 자동 생성 → 학습 목적 확인
- ✅ 루브릭 기반 평가 (우수/양호/미흡)
- ✅ 3회 재시도 + 세션 복원
- ✅ 실시간 피드백 메시지
- ✅ Upstage Solar-pro2 기반 질문 생성

## 개발 상태

- [ ] HTML 레이아웃 (index.html)
- [ ] 상태 머신 구현 (state-machine.js)
- [ ] UI 렌더링 로직 (ui-manager.js)
- [ ] LLM API 연동 (llm-service.js)
- [ ] 세션 관리 (session-manager.js)
- [ ] 통합 테스트

## 아키텍처

```
Express.js 백엔드 (Node.js)
│
├─ 환경변수 로드 (.env)
│  └─ UPSTAGE_API_KEY, UPSTAGE_MODEL 읽음
│
├─ API 라우트
│  ├─ POST /api/generate-question
│  └─ POST /api/evaluate-purpose
│
└─ Upstage API 호출
   └─ solar-pro2 모델

프론트엔드 (HTML/CSS/JS)
│
├─ 상태 머신 (state-machine.js)
├─ UI 관리 (ui-manager.js)
├─ 세션 관리 (session-manager.js)
└─ API 호출 (llm-service.js)
   └─ fetch로 백엔드 /api/* 호출
```

## 환경 변수 (.env)

프로젝트 루트의 `.env` 파일에서 설정:

| 변수 | 설명 | 기본값 |
|------|------|-------|
| UPSTAGE_API_KEY | Upstage API 키 (필수) | - |
| UPSTAGE_MODEL | 모델명 | solar-pro2 |
| TEMPERATURE | 응답 다양성 (0~1) | 0.7 |
| MAX_TOKENS | 최대 응답 길이 | 500 |
| TIMEOUT | API 타임아웃 (ms) | 30000 |
| PORT | 백엔드 포트 | 3000 |

## 주의사항

- 이 MVP는 **기획 문서 검증용 프로토타입**입니다. 프로덕션 수준의 에러 처리, 보안, 성능 최적화는 포함되지 않습니다.
- Upstage API 호출 시 비용이 발생할 수 있습니다. 테스트 시 토큰 제한을 설정하세요.
- 로컬 개발 환경 전용입니다. 프로덕션 배포 시 적절한 보안 설정이 필요합니다.
