/**
 * Session Manager
 * 사용자 입력과 상태를 localStorage에 저장/복원
 */

class SessionManager {
  constructor(storageKey = 'questionCoach_session') {
    this.storageKey = storageKey;
    this.session = this.loadSession();
  }

  loadSession() {
    const stored = localStorage.getItem(this.storageKey);
    if (stored) {
      return JSON.parse(stored);
    }
    return this.createNewSession();
  }

  createNewSession() {
    return {
      step1_subject: '',
      step2_5w1h: {
        When: '',
        Where: '',
        Who: '',
        What: '',
        Why: ''
      },
      step3_learning_purpose: '',
      retry_count: 0,
      generated_question: '',
      feedback_message: '',
      currentScreen: 'start',
      timestamp: Date.now()
    };
  }

  save() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.session));
  }

  get(key) {
    return this.session[key];
  }

  set(key, value) {
    this.session[key] = value;
    this.save();
  }

  update5W1H(field, value) {
    this.session.step2_5w1h[field] = value;
    this.save();
  }

  get5W1H() {
    return this.session.step2_5w1h;
  }

  count5W1HFilled() {
    const { When, Where, Who, What, Why } = this.session.step2_5w1h;
    return [When, Where, Who, What, Why].filter(v => v.trim()).length;
  }

  incrementRetry() {
    this.session.retry_count++;
    this.save();
  }

  resetRetry() {
    this.session.retry_count = 0;
    this.save();
  }

  clear() {
    localStorage.removeItem(this.storageKey);
    this.session = this.createNewSession();
  }
}
