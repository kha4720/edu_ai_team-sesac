/**
 * Application Main
 * 전체 애플리케이션 조율
 */

class QuestionCoachApp {
  constructor() {
    this.session = new SessionManager();
    this.ui = new UIManager();
    this.stateMachine = new StateMachine();
    this.llmService = new LLMService(CONFIG);

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.restoreSession();
  }

  setupEventListeners() {
    // Start screen
    document.getElementById('btn-start').addEventListener('click', () => this.startSession());

    // Subject screen
    document.getElementById('btn-next-subject').addEventListener('click', () => this.validateAndNextSubject());

    // 5W1H screen
    document.getElementById('btn-next-5w1h').addEventListener('click', () => this.validateAndGenerateQuestion());

    // Draft screen
    document.getElementById('btn-next-draft').addEventListener('click', () => this.goToScreen('purpose'));

    // Purpose screen
    document.getElementById('btn-submit').addEventListener('click', () => this.validateAndEvaluatePurpose());

    // Feedback screen
    document.getElementById('btn-retry').addEventListener('click', () => this.retryQuestion());
    document.getElementById('btn-submit-to-ai').addEventListener('click', () => this.submitToAI());
  }

  restoreSession() {
    const currentScreen = this.session.get('currentScreen');
    if (currentScreen && currentScreen !== 'start') {
      this.ui.showScreen(currentScreen);

      // 이전 입력값 복원
      const subject = this.session.get('step1_subject');
      const topic = this.session.get('step1_topic') || '';
      if (subject) {
        this.ui.setSubjectValues(subject, topic);
      }

      const w1h = this.session.get5W1H();
      if (w1h && w1h.When) {
        this.ui.set5W1HValues(w1h);
      }

      const question = this.session.get('generated_question');
      if (question) {
        this.ui.setQuestion(question);
      }

      const purpose = this.session.get('step3_learning_purpose');
      if (purpose) {
        this.ui.setPurpose(purpose);
      }
    }
  }

  startSession() {
    this.session.clear();
    this.stateMachine.startSession();
    this.goToScreen('subject');
  }

  validateAndNextSubject() {
    const { subject, topic } = this.ui.getSubject();
    const validation = this.stateMachine.validateSubject(subject);

    if (!validation.valid) {
      this.ui.showFeedback('feedback-subject', validation.message, 'error');
      return;
    }

    this.session.set('step1_subject', subject);
    this.session.set('step1_topic', topic);
    this.ui.hideFeedback('feedback-subject');

    this.stateMachine.completeSubjectSelection();
    this.goToScreen('5w1h');
  }

  validateAndGenerateQuestion() {
    const w1h = this.ui.get5W1HValues();
    const validation = this.stateMachine.validateW1H(w1h);

    if (!validation.valid) {
      this.ui.showFeedback('feedback-5w1h', validation.message, 'error');
      return;
    }

    // 5W1H 값 저장
    Object.keys(w1h).forEach(key => {
      this.session.update5W1H(key, w1h[key]);
    });

    // 질문 생성 중...
    this.ui.showLoading('question-textarea');
    this.ui.disableButton('btn-next-5w1h');

    const subject = this.session.get('step1_subject');
    const topic = this.session.get('step1_topic');

    this.llmService.generateQuestion(subject, topic, w1h)
      .then(question => {
        this.session.set('generated_question', question);
        this.ui.setQuestion(question);
        this.ui.enableButton('btn-next-5w1h');
        this.ui.hideFeedback('feedback-5w1h');

        this.stateMachine.completeW1HInput();
        this.goToScreen('draft');
      })
      .catch(error => {
        console.error('생성 실패:', error);
        this.ui.showFeedback('feedback-5w1h', '질문 생성에 실패했습니다: ' + error.message, 'error');
        this.ui.setQuestion('');
        this.ui.enableButton('btn-next-5w1h');
      });
  }

  validateAndEvaluatePurpose() {
    const purpose = this.ui.getPurpose();
    const validation = this.stateMachine.validatePurpose(purpose);

    if (!validation.valid) {
      this.ui.showFeedback('feedback-purpose', validation.message, 'error');
      return;
    }

    this.session.set('step3_learning_purpose', purpose);
    this.ui.disableButton('btn-submit');
    this.ui.showFeedback('feedback-purpose', '평가 중...', 'warning');

    const question = this.session.get('generated_question');

    this.llmService.evaluatePurpose(question, purpose)
      .then(result => {
        const mode = result.mode;
        const feedback = result.feedback;

        this.session.set('feedback_message', feedback);
        this.session.incrementRetry();

        this.stateMachine.completePurposeConfirmation(mode);
        this.goToScreen('feedback');

        this.ui.showFeedbackResult(mode, feedback);
        this.ui.enableButton('btn-submit');
        this.ui.hideFeedback('feedback-purpose');
      })
      .catch(error => {
        console.error('평가 실패:', error);
        this.ui.showFeedback('feedback-purpose', '평가에 실패했습니다: ' + error.message, 'error');
        this.ui.enableButton('btn-submit');
      });
  }

  retryQuestion() {
    const retryCount = this.session.get('retry_count');

    if (retryCount >= 3) {
      // 3회 이상 실패 시 주제 선정으로
      alert('주제를 다시 선택해 주세요');
      this.startSession();
    } else {
      // 5W1H 재입력
      this.stateMachine.retryFromFeedback();
      this.goToScreen('5w1h');
    }
  }

  submitToAI() {
    alert('🎉 질문이 AI에 전송되었습니다!\n\n이제 AI가 당신의 질문에 답변해줄 준비가 되었습니다.');
    this.startSession();
  }

  goToScreen(screenName) {
    this.ui.showScreen(screenName);
    this.session.set('currentScreen', screenName);
  }
}

// 애플리케이션 시작
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new QuestionCoachApp();
});
