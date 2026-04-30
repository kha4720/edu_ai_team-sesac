# Interface Spec

## 1. API 명세
### POST /generate-question
- **요청 바디**:  
  ```json
  {
    "step1_subject": "string",
    "step2_5w1h": {
      "When": "string",
      "Where": "string",
      "Who": "string",
      "What": "string",
      "Why": "string"
    }
  }
  ```
- **응답 바디**:  
  ```json
  {
    "generated_question": "string",
    "feedback_message": "string",
    "mode": "string",
    "required_retry_fields": ["string"]
  }
  ```
- **에러 응답**:  
  - `400 Bad Request`: 필수 필드 누락 시  
    ```json
    { "error": "필수 입력 항목을 확인해 주세요" }
    ```
  - `500 Internal Server Error`: LLM API 호출 실패 시  
    ```json
    { "error": "일시적인 오류가 발생했습니다" }
    ```

### POST /evaluate-purpose
- **요청 바디**:  
  ```json
  {
    "step3_learning_purpose": "string"
  }
  ```
- **응답 바디**:  
  ```json
  {
    "feedback_message": "string",
    "mode": "string"
  }
  ```
- **에러 응답**:  
  - `400 Bad Request`: 학습 목적 미입력 시  
    ```json
    { "error": "목적을 간단히 적어 주세요" }
    ```

## 2. UI 인터랙션 정의
| 화면 | 사용자 액션 | 요청 API | mode 별 렌더링 |
|------|------------|---------|--------------|
| **2.0 주제 선정 단계** | "다음" 클릭 | - | 주제 미선택 시 경고 메시지 표시 |
| **3.0 5W1H 요소 확인 단계** | "다음" 클릭 | POST /generate-question | - **우수/양호**: 자동 생성된 질문 문장 표시<br>- **미흡**: 누락된 5W1H 요소 재입력 유도 |
| **4.0 문장 완성 단계** | "학습 목적 확인" 클릭 | - | 문장 수정 가능 텍스트 필드 제공 |
| **5.0 학습 목적 확인 단계** | "질문 제출" 클릭 | POST /evaluate-purpose | - **우수**: "AI 질문 전송" 버튼 활성화<br>- **양호**: "수정 후 재시도" 또는 "AI 질문 전송" 선택 제공<br>- **미흡**: "처음부터 다시 시작" 권장 메시지 표시 |
| **6.0 피드백 결과 화면** | "다시 시도" 클릭 | - | 이전 입력값 유지하며 3.0/5.0 단계로 복귀 |

## 3. 모듈 간 연결 구조
1. **3단계 스캐폴딩 UI 모듈** → (주제/5W1H 입력) → **5W1H 검증 모듈**  
   - 필수 입력 항목 검증 후 다음 단계 진행 신호 전달  
2. **5W1H 검증 모듈** → (검증 통과 시) → **LLM 기반 질문 생성 API**  
   - 주제+5W1H 요소로 질문 문장 생성 요청  
3. **LLM 기반 질문 생성 API** → (생성된 질문 반환) → **학습 목적 확인 모듈**  
   - 생성된 질문 문장 표시 및 학습 목적 입력 유도  
4. **학습 목적 확인 모듈** → (목적 입력) → **LLM 기반 연결성 평가 API**  
   - 학습 목적 연결성 평가 후 피드백 메시지 반환  
5. **순차적 피드백 모듈** → (평가 결과 기반) → UI 렌더링  
   - mode 값에 따라 재시도/전송/종료 유도  

## 4. 세션 내 공유 컨텍스트
| 데이터 항목 | 생성 시점 (API) | 사용 시점 (API) | 관리 주체 (프론트/백엔드) |
|------------|---------------|---------------|------------------------|
| **step1_subject** | 2.0 주제 선정 단계 | 모든 API 요청 | 프론트엔드 (로컬 스토리지) |
| **step2_5w1h** | 3.0 5W1H 요소 확인 단계 | POST /generate-question | 프론트엔드 (세션 메모리) |
| **step3_learning_purpose** | 5.0 학습 목적 확인 단계 | POST /evaluate-purpose | 프론트엔드 (세션 메모리) |
| **retry_count** | 6.0 피드백 결과 화면 | 모든 재시도 요청 | 프론트엔드 (세션 메모리)<br>- 3회 초과 시 초기화 |
| **generated_question** | POST /generate-question | 4.0 문장 완성 단계 | 프론트엔드 (세션 메모리) |
| **feedback_message** | POST /evaluate-purpose | 6.0 피드백 결과 화면 | 프론트엔드 (세션 메모리) |