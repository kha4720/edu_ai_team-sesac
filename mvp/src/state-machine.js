/**
 * State Machine
 * 사용자 흐름과 상태 전이 로직
 */

class StateMachine {
  constructor() {
    this.state = 'START';
    this.states = {
      START: 'start',
      SUBJECT_SELECTED: 'subject',
      W1H_INPUT: '5w1h',
      QUESTION_DRAFT: 'draft',
      PURPOSE_CONFIRM: 'purpose',
      FEEDBACK_EXCELLENT: 'feedback',
      FEEDBACK_GOOD: 'feedback',
      FEEDBACK_POOR: 'feedback',
      RETRY: '5w1h',
      ERROR: 'error'
    };
  }

  transitionTo(newState) {
    if (this.states[newState]) {
      this.state = newState;
      return true;
    }
    console.warn(`Unknown state: ${newState}`);
    return false;
  }

  getScreenForState(state = this.state) {
    return this.states[state];
  }

  getCurrentScreen() {
    return this.getScreenForState();
  }

  // 상태 전이 규칙
  startSession() {
    this.transitionTo('SUBJECT_SELECTED');
  }

  completeSubjectSelection() {
    this.transitionTo('W1H_INPUT');
  }

  completeW1HInput() {
    this.transitionTo('QUESTION_DRAFT');
  }

  completePurposeConfirmation(mode) {
    if (mode === '우수') {
      this.transitionTo('FEEDBACK_EXCELLENT');
    } else if (mode === '양호') {
      this.transitionTo('FEEDBACK_GOOD');
    } else {
      this.transitionTo('FEEDBACK_POOR');
    }
  }

  retryFromFeedback() {
    this.transitionTo('RETRY');
  }

  resetToStart() {
    this.transitionTo('START');
  }

  goToError() {
    this.transitionTo('ERROR');
  }

  // 조건부 전이
  validateSubject(subject) {
    if (!subject || subject.trim() === '') {
      return { valid: false, message: '주제를 선택해 주세요' };
    }
    return { valid: true };
  }

  validateW1H(w1h) {
    const filledCount = Object.values(w1h)
      .filter(v => v && v.trim() !== '')
      .length;

    if (filledCount < 3) {
      return {
        valid: false,
        message: `3개 이상 입력해 주세요 (현재: ${filledCount}/5)`
      };
    }
    return { valid: true };
  }

  validatePurpose(purpose) {
    if (!purpose || purpose.trim() === '') {
      return { valid: false, message: '목적을 간단히 적어 주세요' };
    }
    return { valid: true };
  }
}
