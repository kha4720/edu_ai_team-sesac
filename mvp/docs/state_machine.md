# State Machine

## 1. 상태 목록
| 상태명 | 설명 | 진입 조건 |
|--------|------|-----------|
| **START** | 서비스 시작 상태 | 1.0 시작 화면 진입 시 |
| **SUBJECT_SELECTED** | 주제 선정 완료 상태 | 2.0 주제 선정 단계에서 과목/주제 선택 완료 |
| **5W1H_INPUT** | 5W1H 요소 입력 상태 | 3.0 5W1H 요소 확인 단계에서 3개 이상 입력 완료 |
| **QUESTION_DRAFT** | 질문 문장 생성 상태 | 4.0 문장 완성 단계에서 LLM이 질문 문장 생성 완료 |
| **PURPOSE_CONFIRM** | 학습 목적 확인 상태 | 5.0 학습 목적 확인 단계에서 목적 입력 완료 |
| **FEEDBACK_EXCELLENT** | 우수 평가 상태 | output.mode = "우수" |
| **FEEDBACK_GOOD** | 양호 평가 상태 | output.mode = "양호" |
| **FEEDBACK_POOR** | 미흡 평가 상태 | output.mode = "미흡" |
| **RETRY** | 재시도 상태 | output.mode = "재도전" 또는 사용자 "다시 시도" 요청 |
| **ERROR** | 시스템 오류 상태 | LLM API 호출 실패 또는 빈 입력 발생 시 |

## 2. 상태 전이 규칙

### START
- IF "질문 생성 시작" 클릭: THEN → **SUBJECT_SELECTED**  
- IF "이전 질문 수정하기" 클릭: THEN → **5W1H_INPUT** (이전 입력값 복원)

### SUBJECT_SELECTED
- IF 주제 미선택: THEN → **START** (경고 메시지 표시)  
- IF 주제 선택 완료: THEN → **5W1H_INPUT**

### 5W1H_INPUT
- IF 필수 요소 3개 미만: THEN → **5W1H_INPUT** (안내 메시지 표시)  
- IF 3개 이상 입력: THEN → **QUESTION_DRAFT**  
- IF "다시 시작" 요청: THEN → **START**

### QUESTION_DRAFT
- IF 문장 수정 후 "학습 목적 확인" 클릭: THEN → **PURPOSE_CONFIRM**  
- IF "다시 시작" 요청: THEN → **START**

### PURPOSE_CONFIRM
- IF 학습 목적 미입력: THEN → **PURPOSE_CONFIRM** (안내 메시지 표시)  
- IF 목적 입력 완료: THEN → **FEEDBACK_EXCELLENT** / **FEEDBACK_GOOD** / **FEEDBACK_POOR** (LLM 평가 결과 기반)

### FEEDBACK_EXCELLENT
- IF "AI 질문 전송" 선택: THEN → **START** (전송 후 종료)  
- IF "학습 노트 저장" 선택: THEN → **START** (저장 후 종료)  
- IF "다시 시도" 선택: THEN → **RETRY**

### FEEDBACK_GOOD
- IF "수정 후 재시도" 선택: THEN → **RETRY**  
- IF "AI 질문 전송" 선택: THEN → **START** (전송 후 종료)  
- IF "다시 시작" 선택: THEN → **START**

### FEEDBACK_POOR
- IF 1개 항목 미달: THEN → **RETRY** (해당 항목 보완 유도)  
- IF 2개 이상 항목 미달: THEN → **START** (처음부터 재시작 권장)  
- IF "다시 시도" 선택: THEN → **RETRY**

### RETRY
- IF 3회 미만 시도: THEN → **5W1H_INPUT** / **PURPOSE_CONFIRM** (이전 입력값 유지)  
- IF 3회 이상 시도: THEN → **SUBJECT_SELECTED** (주제 선정 단계로 복귀)

### ERROR
- IF 시스템 오류 발생: THEN → **ERROR** (에러 메시지 표시 후 30초 후 **START**로 복귀)  
- IF 빈 입력 발생: THEN → **ERROR** (에러 메시지 표시 후 해당 입력 단계로 복귀)

## 3. data_schema mode 값 매핑 규칙
| mode 값 | 대응 상태 | 설명 |
|---------|----------|------|
| "우수" | **FEEDBACK_EXCELLENT** | 모든 평가축에서 "우수" 또는 "양호" 충족 시 |
| "양호" | **FEEDBACK_GOOD** | 최소 성취 기준(양호 이상) 충족 시 |
| "미흡" | **FEEDBACK_POOR** | 1~2개 평가축에서 "미흡" 발생 시 |
| "재도전" | **RETRY** | 3회 미만 시도에서 재시도 요청 시 |

## 4. 예외 처리 및 에러 메시지
| 예외 상황 | 에러 메시지 | 전이 상태 |
|----------|------------|----------|
| 주제 미선택 | "주제를 선택해 주세요" | **START** |
| 5W1H 요소 3개 미만 | "3개 이상 입력해 주세요" | **5W1H_INPUT** |
| 학습 목적 미입력 | "목적을 간단히 적어 주세요" | **PURPOSE_CONFIRM** |
| LLM API 호출 실패 | "일시적인 오류가 발생했습니다. 다시 시도해 주세요." | **ERROR** |
| 3회 연속 "미흡" | "주제 선정 단계로 복귀할까요?" | **SUBJECT_SELECTED** |
| 30분 미활동 | "다시 질문 생성할까요?" | **START** |

## 5. data_schema mode 값 매핑
| mode 값 | UI 렌더링 | 피드백 분기 | 다음 동작 |
|---------|----------|-------------|------------|
| "우수" | "질문이 명확하고 학습 목표와 연결됩니다!" | AI 질문 전송 버튼 활성화 + 학습 노트 저장 제안 | 전송 / 저장 / 재시도 |
| "양호" | "질문이 대체로 명확하지만, [누락 요소]를 추가하면 더 정확해질 거예요" | 수정 후 재시도 또는 AI 질문 전송 선택 제공 | 수정 / 전송 / 재시작 |
| "미흡" | "아직 질문이 명확하지 않아요. [주제]와 [5W1H 요소 3개]를 포함해 다시 질문해 볼까요?" | 처음부터 다시 시작 권장 | 재시작 / 재시도 |
| "재도전" | "3회 시도 중 [N]회 성공했어요! 모호한 부분을 다시 점검해 볼까요?" | 이전 시도 기록 표시 + 수정 유도 | 수정 / 재시작 |