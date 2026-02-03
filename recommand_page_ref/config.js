// 종가 베팅 대시보드 - 키움 REST API 설정
// 모든 인증 정보는 프로젝트 루트의 .env 파일에서 관리합니다

const KIWOOM_CONFIG = {
    // ========================================
    // 🔑 키움 REST API 인증 정보
    // .env 파일에서 설정합니다:
    // - KIWOOM_APP_KEY
    // - KIWOOM_SECRET_KEY
    // ========================================

    APP_KEY: '', // process.env.KIWOOM_APP_KEY 사용 권장
    APP_SECRET: '', // process.env.KIWOOM_SECRET_KEY 사용 권장

    // ========================================
    // 서버 설정 (기본값 - 수정 불필요)
    // ========================================

    // 키움증권 REST API 서버
    REAL_SERVER: 'https://api.kiwoom.com',

    // 모의투자 서버 (키움 REST API는 현재 실전 중심)
    MOCK_SERVER: 'https://mockapi.kiwoom.com',

    // 사용할 서버 선택 (true: 실전, false: 모의)
    USE_REAL_SERVER: true,

    // ========================================
    // 종목 설정
    // ========================================

    // 종가베팅 대상 종목 리스트 (변동 데이터 사용을 위해 비워둠)
    WATCHLIST: [],

    // 데이터 갱신 주기 (밀리초)
    REFRESH_INTERVAL: 10000,

    // ========================================
    // 텔레그램 알림 설정
    // .env 파일에서 설정합니다:
    // - TELEGRAM_BOT_TOKEN
    // - TELEGRAM_CHAT_ID
    // ========================================
    TELEGRAM: {
        ENABLE: false,
        BOT_TOKEN: '', // process.env.TELEGRAM_BOT_TOKEN 사용 권장
        CHAT_ID: '', // process.env.TELEGRAM_CHAT_ID 사용 권장
        SEND_TIME: '15:20' // 장 마감 직전 추천 및 데이터 저장 시간 (HH:mm)
    }
};

// 설정 내보내기
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KIWOOM_CONFIG;
}
