/**
 * LLM Service
 * 백엔드 API를 통한 질문 생성 및 평가
 */

class LLMService {
  constructor(config) {
    this.config = config;
    this.timeout = config.api.timeout;
  }

  async generateQuestion(subject, topic, w1h) {
    try {
      const response = await fetch('/api/generate-question', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ subject, topic, w1h }),
        signal: AbortSignal.timeout(this.timeout)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || '질문 생성 실패');
      }

      const data = await response.json();
      return data.generated_question;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('API 요청 시간 초과. 다시 시도해주세요.');
      }
      throw error;
    }
  }

  async evaluatePurpose(question, purpose) {
    try {
      const response = await fetch('/api/evaluate-purpose', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question, purpose }),
        signal: AbortSignal.timeout(this.timeout)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || '평가 실패');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('API 요청 시간 초과. 다시 시도해주세요.');
      }
      throw error;
    }
  }

}
