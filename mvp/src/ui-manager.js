/**
 * UI Manager
 * 화면 렌더링과 사용자 상호작용 처리
 */

class UIManager {
  constructor() {
    this.screens = {
      'start': 'screen-start',
      'subject': 'screen-subject',
      '5w1h': 'screen-5w1h',
      'draft': 'screen-draft',
      'purpose': 'screen-purpose',
      'feedback': 'screen-feedback'
    };
  }

  showScreen(screenName) {
    // 모든 화면 숨기기
    Object.values(this.screens).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    // 해당 화면 표시
    const screenId = this.screens[screenName];
    if (screenId) {
      const el = document.getElementById(screenId);
      if (el) el.classList.add('active');
    }

    this.updateProgressBar(screenName);
  }

  updateProgressBar(screenName) {
    const screens = ['start', 'subject', '5w1h', 'draft', 'purpose', 'feedback'];
    const index = screens.indexOf(screenName);
    const progress = ((index + 1) / screens.length) * 100;
    const fillEl = document.getElementById('progressFill');
    if (fillEl) {
      fillEl.style.width = progress + '%';
    }
  }

  showFeedback(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (el) {
      el.textContent = message;
      el.className = `feedback ${type}`;
      el.style.display = 'block';
    }
  }

  hideFeedback(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
      el.style.display = 'none';
    }
  }

  showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
      el.innerHTML = '<span class="loading"></span> 생성 중...';
    }
  }

  // Subject 화면
  getSubject() {
    const select = document.getElementById('subject-select');
    const input = document.getElementById('topic-input');
    return {
      subject: select.value,
      topic: input.value
    };
  }

  setSubjectValues(subject, topic) {
    document.getElementById('subject-select').value = subject;
    document.getElementById('topic-input').value = topic;
  }

  // 5W1H 화면
  get5W1HValues() {
    return {
      When: document.getElementById('when-input').value,
      Where: document.getElementById('where-input').value,
      Who: document.getElementById('who-input').value,
      What: document.getElementById('what-input').value,
      Why: document.getElementById('why-input').value
    };
  }

  set5W1HValues(w1h) {
    document.getElementById('when-input').value = w1h.When || '';
    document.getElementById('where-input').value = w1h.Where || '';
    document.getElementById('who-input').value = w1h.Who || '';
    document.getElementById('what-input').value = w1h.What || '';
    document.getElementById('why-input').value = w1h.Why || '';
  }

  // Draft 화면
  getQuestion() {
    return document.getElementById('question-textarea').value;
  }

  setQuestion(question) {
    document.getElementById('question-textarea').value = question;
  }

  // Purpose 화면
  getPurpose() {
    return document.getElementById('purpose-textarea').value;
  }

  setPurpose(purpose) {
    document.getElementById('purpose-textarea').value = purpose;
  }

  // Feedback 화면
  showFeedbackResult(mode, feedback) {
    const container = document.getElementById('feedback-result');
    let badgeClass = '';
    let modeLabel = '';

    if (mode === '우수') {
      badgeClass = 'excellent';
      modeLabel = '✨ 우수';
    } else if (mode === '양호') {
      badgeClass = 'good';
      modeLabel = '👍 양호';
    } else {
      badgeClass = 'poor';
      modeLabel = '⚠️ 미흡';
    }

    container.innerHTML = `<div class="badge ${badgeClass}">${modeLabel}</div>`;

    const msgEl = document.getElementById('feedback-message');
    msgEl.textContent = feedback;
    msgEl.className = 'feedback success';
    msgEl.style.display = 'block';

    // 모드에 따라 버튼 표시
    const retryBtn = document.getElementById('btn-retry');
    const submitBtn = document.getElementById('btn-submit-to-ai');

    if (mode === '우수') {
      retryBtn.style.display = 'inline-block';
      submitBtn.style.display = 'inline-block';
    } else if (mode === '양호') {
      retryBtn.style.display = 'inline-block';
      submitBtn.style.display = 'inline-block';
    } else {
      retryBtn.style.display = 'inline-block';
      submitBtn.style.display = 'none';
    }
  }

  disableButton(elementId) {
    const btn = document.getElementById(elementId);
    if (btn) {
      btn.disabled = true;
      btn.style.opacity = '0.5';
    }
  }

  enableButton(elementId) {
    const btn = document.getElementById(elementId);
    if (btn) {
      btn.disabled = false;
      btn.style.opacity = '1';
    }
  }
}
