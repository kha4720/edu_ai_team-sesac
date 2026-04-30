/**
 * MVP Backend Server
 * Express.js 기반 로컬 개발 서버
 *
 * 실행: node server.js
 * 접속: http://localhost:3000
 */

require('dotenv').config();
const express = require('express');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 환경 변수
const UPSTAGE_API_KEY = process.env.UPSTAGE_API_KEY;
const UPSTAGE_MODEL = process.env.UPSTAGE_MODEL || 'solar-pro2';
const API_BASE_URL = 'https://api.upstage.ai/v1';

if (!UPSTAGE_API_KEY) {
  console.error('❌ 오류: UPSTAGE_API_KEY가 설정되지 않았습니다.');
  console.error('   .env 파일에 UPSTAGE_API_KEY를 입력하세요.');
  process.exit(1);
}

console.log('✅ Upstage API 설정 완료');
console.log(`   모델: ${UPSTAGE_MODEL}`);

// =============================================================================
// API Routes
// =============================================================================

/**
 * POST /api/generate-question
 * 질문 자동 생성
 */
app.post('/api/generate-question', async (req, res) => {
  try {
    const { subject, topic, w1h } = req.body;

    if (!subject || !w1h) {
      return res.status(400).json({ error: '필수 입력 항목을 확인해 주세요' });
    }

    const prompt = `
다음 정보를 바탕으로 명확하고 구체적인 학습 질문 1개를 생성해주세요.

주제: ${subject} - ${topic || ''}

5W1H 요소:
- When: ${w1h.When || ''}
- Where: ${w1h.Where || ''}
- Who: ${w1h.Who || ''}
- What: ${w1h.What || ''}
- Why: ${w1h.Why || ''}

요구사항:
1. 한국어로 작성
2. 한 문장으로 완성
3. 5W1H 요소를 자연스럽게 통합
4. 질문 기호(?)로 끝남

생성된 질문:`;

    const response = await callUpstageAPI(prompt);
    res.json({ generated_question: response });
  } catch (error) {
    console.error('생성 실패:', error.message);
    res.status(500).json({ error: '질문 생성에 실패했습니다: ' + error.message });
  }
});

/**
 * POST /api/evaluate-purpose
 * 학습 목적 연결성 평가
 */
app.post('/api/evaluate-purpose', async (req, res) => {
  try {
    const { question, purpose } = req.body;

    if (!question || !purpose) {
      return res.status(400).json({ error: '필수 입력 항목을 확인해 주세요' });
    }

    const prompt = `
다음 질문과 학습 목적이 얼마나 잘 연결되어 있는지 평가해주세요.

질문: ${question}
학습 목적: ${purpose}

평가 기준:
- 우수: 질문과 목적이 매우 명확하게 연결됨
- 양호: 대체로 잘 맞음. 개선 가능한 부분이 약간 있음
- 미흡: 질문과 목적이 명확하지 않거나 관련성이 낮음

다음 JSON 형식으로 응답해주세요:
{
  "mode": "우수|양호|미흡",
  "feedback": "피드백 메시지"
}`;

    const response = await callUpstageAPI(prompt);

    try {
      const parsed = JSON.parse(response);
      res.json(parsed);
    } catch {
      // JSON 파싱 실패 시 텍스트로 반환
      res.json({
        mode: '양호',
        feedback: response
      });
    }
  } catch (error) {
    console.error('평가 실패:', error.message);
    res.status(500).json({ error: '평가에 실패했습니다: ' + error.message });
  }
});

// =============================================================================
// Upstage API Helper
// =============================================================================

async function callUpstageAPI(prompt) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/chat/completions`,
      {
        model: UPSTAGE_MODEL,
        messages: [
          {
            role: 'system',
            content: '당신은 중학생을 위한 AI 학습 조력자입니다. 한국어로만 답변하세요.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: parseFloat(process.env.TEMPERATURE || '0.7'),
        max_tokens: parseInt(process.env.MAX_TOKENS || '500')
      },
      {
        headers: {
          'Authorization': `Bearer ${UPSTAGE_API_KEY}`,
          'Content-Type': 'application/json'
        },
        timeout: parseInt(process.env.TIMEOUT || '30000')
      }
    );

    return response.data.choices[0].message.content.trim();
  } catch (error) {
    if (error.response) {
      throw new Error(`Upstage API 오류: ${error.response.data?.error?.message || '요청 실패'}`);
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('API 요청 시간 초과');
    } else {
      throw error;
    }
  }
}

// =============================================================================
// Static Routes
// =============================================================================

// 루트 경로 → index.html
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// =============================================================================
// Error Handler
// =============================================================================

app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({ error: '서버 오류가 발생했습니다' });
});

// =============================================================================
// Server Start
// =============================================================================

app.listen(PORT, () => {
  console.log(`\n🚀 Question Coach MVP Server`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`📌 로컬 주소: http://localhost:${PORT}`);
  console.log(`🌐 원격 주소: http://localhost:${PORT}`);
  console.log(`\n🎯 API 엔드포인트:`);
  console.log(`   POST /api/generate-question   - 질문 생성`);
  console.log(`   POST /api/evaluate-purpose    - 목적 평가`);
  console.log(`\n⚠️  종료: CTRL+C`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
});
