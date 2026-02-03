// 종가 베팅 대시보드 - 키움 REST API 설정
// 여기에 키움 REST API 인증 정보를 입력하세요

const KIWOOM_CONFIG = {
    // ========================================
    // 🔑 키움 REST API 인증 정보 입력
    // ========================================

    // API 키 (발급받은 appkey 입력)
    APP_KEY: 'd9ke3uKB52_OXx9lpKBruO2IaB1m4jz7cg6KGPWRITQ',

    // 시크릿 키 (발급받은 appsecret 입력)
    APP_SECRET: 'qctCqqSPMtZelgcsS6-Ldx_w03Xdi2t_GFm7GfHIBJc',

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
    // ========================================
    TELEGRAM: {
        ENABLE: false,
        BOT_TOKEN: '8206855941:AAGdXPfxfaGCfVstzZMfG4a97qsqdeD9GCY',
        CHAT_ID: 'YOUR_TELEGRAM_CHAT_ID_HERE',
        SEND_TIME: '15:20' // 장 마감 직전 추천 및 데이터 저장 시간 (HH:mm)
    }
};

// 설정 내보내기
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KIWOOM_CONFIG;
}
