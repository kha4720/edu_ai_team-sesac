/**
 * Configuration for MVP
 *
 * .env 파일에서 환경 변수를 읽어옵니다.
 *
 * 사용 방법:
 * 1. .env.example 을 .env 로 복사
 * 2. .env 에서 SOLAR_API_KEY 등 설정
 * 3. 브라우저에서 http://localhost:8000 접속
 */

// 기본값 정의
const ENV = {
  UPSTAGE_API_KEY: process.env?.UPSTAGE_API_KEY || '',
  UPSTAGE_MODEL: process.env?.UPSTAGE_MODEL || 'solar-pro2',
  TEMPERATURE: parseFloat(process.env?.TEMPERATURE || '0.7'),
  MAX_TOKENS: parseInt(process.env?.MAX_TOKENS || '500'),
  TIMEOUT: parseInt(process.env?.TIMEOUT || '30000'),
  MAX_RETRIES: parseInt(process.env?.MAX_RETRIES || '3'),
  SESSION_TIMEOUT: parseInt(process.env?.SESSION_TIMEOUT || '1800000'),
  THEME: process.env?.THEME || 'light',
  LANGUAGE: process.env?.LANGUAGE || 'ko',
  AUTO_SAVE: process.env?.AUTO_SAVE === 'true',
  DEBUG: process.env?.DEBUG === 'true',
};

const CONFIG = {
  // Upstage Solar API 설정
  api: {
    provider: 'upstage',
    apiKey: ENV.UPSTAGE_API_KEY,
    baseUrl: 'https://api.upstage.ai/v1',
    model: ENV.UPSTAGE_MODEL,
    temperature: ENV.TEMPERATURE,
    maxTokens: ENV.MAX_TOKENS,
    timeout: ENV.TIMEOUT,
  },

  // 세션 설정
  session: {
    maxRetries: ENV.MAX_RETRIES,
    sessionTimeout: ENV.SESSION_TIMEOUT,
    storageType: 'localStorage',
  },

  // UI 설정
  ui: {
    theme: ENV.THEME,
    language: ENV.LANGUAGE,
    autoSave: ENV.AUTO_SAVE,
  },

  // 디버그
  debug: ENV.DEBUG,
};
