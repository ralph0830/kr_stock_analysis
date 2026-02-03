/**
 * 종가 베팅 대시보드 - 백엔드 서버
 * 키움증권 REST API 프록시 서버
 */

const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
const path = require('path');

// 설정 불러오기
let UI_CONFIG = null;
try {
    UI_CONFIG = require('./config');
} catch (e) {
    console.warn('⚠️ config.js를 찾을 수 없습니다.');
}

const fs = require('fs');
const historyFilePath = path.join(__dirname, 'history.json');

const app = express();
const PORT = 3005;

// ========================================
// 🔑 키움증권 REST API 설정
// ========================================
const KIWOOM_CONFIG = {
    APP_KEY: process.env.KIWOOM_APP_KEY || (UI_CONFIG && UI_CONFIG.APP_KEY && !UI_CONFIG.APP_KEY.includes('YOUR_') ? UI_CONFIG.APP_KEY : 'd9ke3uKB52_OXx9lpKBruO2IaB1m4jz7cg6KGPWRITQ'),
    SECRET_KEY: process.env.KIWOOM_SECRET_KEY || (UI_CONFIG && UI_CONFIG.APP_SECRET && !UI_CONFIG.APP_SECRET.includes('YOUR_') ? UI_CONFIG.APP_SECRET : 'qctCqqSPMtZelgcsS6-Ldx_w03Xdi2t_GFm7GfHIBJc'),
    USE_REAL_SERVER: (UI_CONFIG && UI_CONFIG.hasOwnProperty('USE_REAL_SERVER')) ? UI_CONFIG.USE_REAL_SERVER : true,
    // 키움증권 REST API 서버
    REAL_SERVER: 'https://api.kiwoom.com',
    MOCK_SERVER: 'https://mockapi.kiwoom.com'
};

const axios = require('axios');
const cheerio = require('cheerio');

// 토큰 저장
let accessToken = null;
let tokenExpiry = null;

// 종목 정보 캐시 (API 제한 방지용)
const stockCache = new Map();
const newsCache = new Map(); // 뉴스 캐시 추가
const CACHE_TTL = 30000; // 30초 캐시 (데이터 안정성 확보)
const NEWS_CACHE_TTL = 300000; // 뉴스 5분 캐시 (네이버 부하 방지)

// 미들웨어
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// 헬스체크
app.get('/health', (req, res) => res.json({ status: 'ok', time: new Date().toISOString() }));

// 서버 URL
const getBaseUrl = () => KIWOOM_CONFIG.USE_REAL_SERVER
    ? KIWOOM_CONFIG.REAL_SERVER
    : KIWOOM_CONFIG.MOCK_SERVER;

// ========================================
// 토큰 발급 (키움증권 REST API)
// ========================================
async function getAccessToken() {
    try {
        console.log('🔐 키움증권 토큰 발급 요청...');
        console.log(`   서버: ${getBaseUrl()}`);

        const response = await fetch(`${getBaseUrl()}/oauth2/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json;charset=UTF-8' },
            body: JSON.stringify({
                grant_type: 'client_credentials',
                appkey: KIWOOM_CONFIG.APP_KEY,
                secretkey: KIWOOM_CONFIG.SECRET_KEY  // 키움은 secretkey 사용
            })
        });

        const data = await response.json();
        console.log('   응답:', JSON.stringify(data).substring(0, 200));

        if (data.token || data.access_token) {
            accessToken = data.token || data.access_token;
            // 키움 토큰은 보통 24시간 유효
            tokenExpiry = Date.now() + (23 * 60 * 60 * 1000);
            console.log('✅ 토큰 발급 성공');



            return true;
        } else {
            console.error('❌ 토큰 발급 실패:', data);
            return false;
        }
    } catch (error) {
        console.error('❌ 토큰 발급 오류:', error.message);
        return false;
    }
}

async function ensureValidToken() {
    if (!accessToken || Date.now() >= tokenExpiry) {
        return await getAccessToken();
    }
    return true;
}

// ========================================
// API 라우트
// ========================================

// 토큰 상태 확인
app.get('/api/status', (req, res) => {
    res.json({
        hasToken: !!accessToken,
        isValid: accessToken && Date.now() < tokenExpiry,
        configValid: KIWOOM_CONFIG.APP_KEY && !KIWOOM_CONFIG.APP_KEY.includes('YOUR_'),
        keySource: (UI_CONFIG && UI_CONFIG.APP_KEY && !UI_CONFIG.APP_KEY.includes('YOUR_')) ? 'config.js' : 'defaults/env',
        server: getBaseUrl()
    });
});

// 토큰 발급/갱신
app.post('/api/token', async (req, res) => {
    const success = await getAccessToken();
    res.json({ success, hasToken: !!accessToken });
});

// 시장 주도주(거래대금 상위) 검색 함수
async function fetchMarketLeaderCodes() {
    try {
        const markets = ['001', '101']; // KOSPI, KOSDAQ
        let leaderCodes = [];

        for (const market of markets) {
            console.log(`📡 [Helper] 시장 순위 조회: ${market}`);
            const response = await fetch(
                `${getBaseUrl()}/api/dostk/rkinfo`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json;charset=UTF-8',
                        'Authorization': `Bearer ${accessToken}`,
                        'appkey': KIWOOM_CONFIG.APP_KEY,
                        'api-id': 'ka10032'
                    },
                    body: JSON.stringify({
                        mrkt_tp: market,
                        mang_stk_incls: '1',
                        stex_tp: '1'
                    })
                }
            );

            const data = await response.json();
            const list = data.trde_prica_upper || data.items || [];
            if (Array.isArray(list)) {
                leaderCodes = leaderCodes.concat(list.map(item => item.stk_cd || item.code).filter(Boolean));
            }
        }
        return [...new Set(leaderCodes)].slice(0, 60);
    } catch (e) {
        console.error('시장 주도주 코드 검색 실패:', e);
        return [];
    }
}

// 주식 현재가 조회 (키움증권 REST API)
app.get('/api/stock/:code', async (req, res) => {
    try {
        if (!await ensureValidToken()) {
            return res.status(401).json({ error: '토큰 발급 실패' });
        }

        const stockCode = req.params.code;

        // 키움증권 종목정보 API (ka10001)
        const response = await fetch(
            `${getBaseUrl()}/api/dostk/stkinfo`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': `Bearer ${accessToken}`,
                    'appkey': KIWOOM_CONFIG.APP_KEY,
                    'api-id': 'ka10001'
                },
                body: JSON.stringify({
                    stk_cd: stockCode
                })
            }
        );

        const data = await response.json();
        console.log(`종목 ${stockCode} 응답:`, JSON.stringify(data).substring(0, 300));

        if (data.cur_prc || data.stk_cd) {
            // 부호 포함 숫자 파싱 함수
            const parseSignedNum = (val) => {
                if (!val) return 0;
                return parseInt(String(val).replace(/[+,]/g, '')) || 0;
            };

            // 키움 API 응답 형식에 맞게 파싱
            res.json({
                success: true,
                data: {
                    code: stockCode,
                    name: data.stk_nm || '',
                    price: parseSignedNum(data.cur_prc),
                    change: parseSignedNum(data.pred_pre),
                    changeRate: parseFloat(String(data.flu_rt).replace('+', '')) || 0,
                    high: parseSignedNum(data.high_pric),
                    low: parseSignedNum(data.low_pric),
                    open: parseSignedNum(data.open_pric),
                    volume: parseSignedNum(data.trde_qty),
                    tradingValue: parseSignedNum(data.mac) * 1000000,
                    high52w: parseSignedNum(data['250hgst']),
                    low52w: parseSignedNum(data['250lwst']),
                    per: parseFloat(data.per) || 0,
                    pbr: parseFloat(data.pbr) || 0
                }
            });
        } else {
            res.json({
                success: false,
                error: data.msg || data.message || 'API 오류',
                rawData: data
            });
        }
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// 여러 종목 조회
app.post('/api/stocks', async (req, res) => {
    try {
        if (!await ensureValidToken()) {
            return res.status(401).json({ error: '토큰 발급 실패' });
        }

        const { codes } = req.body;
        if (!codes || !Array.isArray(codes)) {
            return res.status(400).json({ error: 'codes 배열이 필요합니다' });
        }

        const currentNow = Date.now();
        const results = await Promise.allSettled(
            codes.map(async (code, index) => {
                // 캐시 확인
                if (stockCache.has(code)) {
                    const cached = stockCache.get(code);
                    if (currentNow - cached.timestamp < CACHE_TTL) {
                        return { code, data: cached.data };
                    }
                }

                // 요청 간 딜레이 추가 (API 제한 방지: 500ms로 조절)
                // 300ms도 여러 명이 접속하거나 빈번한 요청 시 부족할 수 있음
                await new Promise(resolve => setTimeout(resolve, index * 500));

                try {
                    const response = await fetch(
                        `${getBaseUrl()}/api/dostk/stkinfo`,
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json;charset=UTF-8',
                                'Authorization': `Bearer ${accessToken}`,
                                'appkey': KIWOOM_CONFIG.APP_KEY,
                                'api-id': 'ka10001'
                            },
                            body: JSON.stringify({
                                stk_cd: code
                            })
                        }
                    );
                    const data = await response.json();

                    // 정상 응답인 경우만 캐싱
                    if (data && data.stk_nm) {
                        stockCache.set(code, { data, timestamp: Date.now() });
                    }

                    console.log(`종목 ${code} 응답:`, JSON.stringify(data).substring(0, 100));
                    return { code, data };
                } catch (e) {
                    console.error(`종목 ${code} 조회 실패:`, e.message);
                    return { code, data: { msg: '조회 실패' } };
                }
            })
        );

        // 부호 포함 숫자 파싱 함수
        const parseSignedNum = (val) => {
            if (!val) return 0;
            return parseInt(String(val).replace(/[+,]/g, '')) || 0;
        };

        const stockData = {};
        results.forEach((result) => {
            if (result.status === 'fulfilled') {
                const { code, data } = result.value;
                if (data.cur_prc || data.stk_cd) {
                    stockData[code] = {
                        code,
                        name: data.stk_nm || '',
                        price: parseSignedNum(data.cur_prc),
                        change: parseSignedNum(data.pred_pre),
                        changeRate: parseFloat(String(data.flu_rt || '0').replace('+', '')) || 0,
                        high: parseSignedNum(data.high_pric),
                        low: parseSignedNum(data.low_pric),
                        open: parseSignedNum(data.open_pric),
                        volume: parseSignedNum(data.trde_qty),
                        tradingValue: parseSignedNum(data.mac) * 1000000,
                        high52w: parseSignedNum(data['250hgst']),
                        low52w: parseSignedNum(data['250lwst']),
                        per: parseFloat(data.per) || 0,
                        pbr: parseFloat(data.pbr) || 0
                    };
                }
            }
        });

        res.json({ success: true, data: stockData, count: Object.keys(stockData).length });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// 거래대금 상위 종목 리스트 조회 (프론트엔드용)
app.get('/api/market/rank', async (req, res) => {
    try {
        if (!await ensureValidToken()) {
            return res.status(401).json({ error: '토큰 발급 실패' });
        }

        const market = req.query.market || '001'; // 001 코스피, 101 코스닥
        console.log(`📡 시장 순위 조회 요청: ${market === '001' ? 'KOSPI' : 'KOSDAQ'}`);

        const response = await fetch(
            `${getBaseUrl()}/api/dostk/rkinfo`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': `Bearer ${accessToken}`,
                    'appkey': KIWOOM_CONFIG.APP_KEY,
                    'api-id': 'ka10032'
                },
                body: JSON.stringify({
                    mrkt_tp: market,
                    mang_stk_incls: '1',
                    stex_tp: '1'
                })
            }
        );

        const data = await response.json();
        const items = data.trde_prica_upper || data.items || [];

        res.json({ success: true, data: Array.isArray(items) ? items : [] });
    } catch (error) {
        console.error('시장 순위 조회 오류:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// 분봉 차트 데이터 조회 (ka10080)
app.get('/api/chart/:code', async (req, res) => {
    try {
        if (!await ensureValidToken()) {
            return res.status(401).json({ error: '토큰 발급 실패' });
        }

        const stockCode = req.params.code;
        const tickScope = req.query.tick || '1'; // 1분봉 기본

        console.log(`📊 분봉 차트 조회: ${stockCode} (${tickScope}분봉)`);

        const response = await fetch(
            `${getBaseUrl()}/api/dostk/chart`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': `Bearer ${accessToken}`,
                    'appkey': KIWOOM_CONFIG.APP_KEY,
                    'api-id': 'ka10080'
                },
                body: JSON.stringify({
                    stk_cd: stockCode,
                    tic_scope: tickScope,
                    upd_stkpc_tp: '1' // 수정주가 적용
                })
            }
        );

        const data = await response.json();
        console.log(`차트 응답 수신 완료: ${stockCode}`);

        const output = data.stk_min_pole_chart_qry || data.output || data.items || [];

        if (output && (Array.isArray(output) ? output.length >= 0 : true)) {
            // 분봉 데이터 파싱
            const parseSignedNum = (val) => {
                if (!val) return 0;
                return parseInt(String(val).replace(/[+,]/g, '')) || 0;
            };

            const rawList = Array.isArray(output) ? output : [output];

            // 현재 KST 시각 (HH:mm)
            const now = new Date();
            const nowKST = new Date(now.getTime() + (9 * 60 * 60 * 1000));
            const currentHHmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

            console.log(`📡 현재 서버 시각: ${currentHHmm}, 데이터 개수: ${rawList.length}`);

            const chartData = rawList
                .map(item => {
                    // 시간 처리 (cntr_tm: 20260130143900 또는 stck_cntg_hour: 143900)
                    let rawTime = String(item.cntr_tm || item.stck_cntg_hour || item.time || '');
                    let hh = '', mm = '';

                    if (rawTime.length >= 12) { // YYYYMMDDHHMMSS
                        hh = rawTime.substring(8, 10);
                        mm = rawTime.substring(10, 12);
                    } else if (rawTime.length >= 4) { // HHMMSS or HHMM
                        hh = rawTime.substring(0, 2);
                        mm = rawTime.substring(2, 4);
                    }

                    const timeStr = (hh && mm) ? `${hh}:${mm}` : rawTime;

                    return {
                        time: timeStr,
                        open: parseSignedNum(item.open_pric || item.stck_oprc),
                        high: parseSignedNum(item.high_pric || item.stck_hgpr),
                        low: parseSignedNum(item.low_pric || item.stck_lwpr),
                        close: parseSignedNum(item.cur_prc || item.stck_clpr || item.stck_prpr),
                        volume: parseSignedNum(item.trde_qty || item.cntg_vol || item.acml_vol)
                    };
                })
                .filter(item => {
                    // 1. 유효한 가격이 있는지 확인
                    if (item.open <= 0) return false;
                    // 2. 현재 시각 이후의 데이터는 필터링 (Mock 서버 등에서 미래 데이터 방지)
                    // 단, 오늘 날짜가 아닐 수 있으므로 주의 (장 종료 후 패치 등)
                    // 여기서는 단순히 현재 시각보다 크면 미래로 간주하여 제외 (사용자 요청 반영)
                    if (item.time > currentHHmm && item.time <= '15:30') {
                        // 만약 데이터가 어제 데이터라면 (예: 15:30) 제외하지 않아야 함
                        // 하지만 사용자 리포트에 따르면 14:50에 15:00이 보인다고 하므로 필터링 적용
                        return false;
                    }
                    return true;
                })
                .reverse(); // 시간순 정렬 (과거 -> 현재)

            res.json({ success: true, data: chartData, count: chartData.length });
        } else {
            res.json({
                success: false,
                error: data.return_msg || '데이터가 없습니다.',
                rawData: data
            });
        }
    } catch (error) {
        console.error('차트 조회 오류:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// API 테스트 (디버깅용)
app.get('/api/test', async (req, res) => {
    try {
        console.log('🧪 API 테스트 시작...');

        // 토큰 발급 테스트
        const tokenResult = await getAccessToken();

        if (!tokenResult) {
            return res.json({
                success: false,
                step: 'token',
                message: '토큰 발급 실패',
                config: {
                    server: getBaseUrl(),
                    appKeyLength: KIWOOM_CONFIG.APP_KEY?.length,
                    secretKeyLength: KIWOOM_CONFIG.SECRET_KEY?.length
                }
            });
        }

        // 삼성전자 테스트 조회
        const testCode = '005930';
        const response = await fetch(
            `${getBaseUrl()}/api/dostk/stkinfo`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'Authorization': `Bearer ${accessToken}`,
                    'appkey': KIWOOM_CONFIG.APP_KEY,
                    'api-id': 'ka10001'
                },
                body: JSON.stringify({
                    stk_cd: testCode
                })
            }
        );

        const data = await response.json();

        res.json({
            success: true,
            tokenOk: true,
            testStock: testCode,
            response: data
        });
    } catch (error) {
        res.json({
            success: false,
            error: error.message
        });
    }
});

// ========================================
// 🤖 텔레그램 발송 및 추천 로직
// ========================================

async function sendTopRecommendationsToTelegram() {
    try {
        if (!await ensureValidToken()) return;

        console.log('📊 실시간 데이터 자동 스캔 중 (상위 거래대금)...');

        // 1. 시장 주도주 코드 검색
        let codes = await fetchMarketLeaderCodes();

        // 2. 만약 검색 실패시 고정 리스트라도 사용
        if (codes.length === 0 && UI_CONFIG && UI_CONFIG.WATCHLIST) {
            codes = UI_CONFIG.WATCHLIST.map(s => s.code);
        }

        if (codes.length === 0) return;

        // 3. 상세 정보 조회
        const results = await Promise.allSettled(
            codes.map(async (code, index) => {
                await new Promise(resolve => setTimeout(resolve, index * 100)); // Rate limit 방지
                const response = await fetch(`${getBaseUrl()}/api/dostk/stkinfo`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json;charset=UTF-8',
                        'Authorization': `Bearer ${accessToken}`,
                        'appkey': KIWOOM_CONFIG.APP_KEY,
                        'api-id': 'ka10001'
                    },
                    body: JSON.stringify({ stk_cd: code })
                });
                return { code, data: await response.json() };
            })
        );

        const parseSignedNum = (val) => {
            if (!val) return 0;
            return parseInt(String(val).replace(/[+,]/g, '')) || 0;
        };

        const stocks = [];
        results.forEach((result) => {
            if (result.status === 'fulfilled') {
                const { code, data } = result.value;
                if (data.cur_prc || data.stk_cd) {
                    stocks.push({
                        code,
                        name: data.stk_nm || code,
                        price: parseSignedNum(data.cur_prc),
                        change: parseSignedNum(data.pred_pre),
                        changeRate: parseFloat(String(data.flu_rt || '0').replace('+', '')) || 0,
                        high: parseSignedNum(data.high_pric),
                        low: parseSignedNum(data.low_pric),
                        open: parseSignedNum(data.open_pric),
                        volume: parseSignedNum(data.trde_qty),
                        tradingValue: parseSignedNum(data.mac) * 1000000,
                        high52w: parseSignedNum(data['250hgst']),
                        low52w: parseSignedNum(data['250lwst'])
                    });
                }
            }
        });

        const scoredStocks = stocks.map(stock => {
            let score = 0;
            const checks = [
                { passed: stock.low52w && stock.price > stock.low52w * 1.3, partial: stock.low52w && stock.price > stock.low52w * 1.1 },
                { passed: (stock.tradingValue || 0) >= 100000000000, partial: (stock.tradingValue || 0) >= 50000000000 },
                { passed: stock.changeRate >= 3, partial: stock.changeRate >= 1 },
                { passed: stock.high && stock.price >= stock.high * 0.98, partial: stock.high && stock.price >= stock.high * 0.95 },
                { passed: stock.high52w && stock.price >= stock.high52w * 0.95, partial: stock.high52w && stock.price >= stock.high52w * 0.85 },
                { passed: stock.high52w && stock.price >= stock.high52w * 0.98, partial: stock.high52w && stock.price >= stock.high52w * 0.90 },
                { passed: stock.changeRate >= 2 && stock.price > stock.open, partial: stock.changeRate >= 0 }
            ];
            checks.forEach(check => {
                if (check.passed) score += 15;
                else if (check.partial) score += 8;
            });
            return { ...stock, score: Math.min(score, 100) };
        });

        const top3 = scoredStocks
            .filter(s => s.tradingValue >= 50000000000)
            .sort((a, b) => b.score - a.score || b.changeRate - a.changeRate)
            .slice(0, 3);

        if (top3.length === 0) {
            console.log('⚠️ 추천 가능한 종목이 없습니다.');
            return;
        }

        const dateStr = new Date().toLocaleDateString('ko-KR');
        let message = `🚀 *오늘의 종가배팅 추천 종목* (${dateStr})\n\n`;
        top3.forEach((s, i) => {
            const medal = i === 0 ? '🥇' : (i === 1 ? '🥈' : '🥉');
            message += `${medal} *${s.name}* (${s.code})\n`;
            message += `🔹 현재가: ${s.price.toLocaleString()}원 (${s.changeRate > 0 ? '+' : ''}${s.changeRate}%)\n`;
            message += `🔹 거래대금: ${Math.round(s.tradingValue / 100000000).toLocaleString()}억\n`;
            message += `🔹 AI 스코어: *${s.score}점*\n\n`;
        });
        message += `🔗 [대시보드 확인하기](http://localhost:3005)`;

        if (UI_CONFIG && UI_CONFIG.TELEGRAM && UI_CONFIG.TELEGRAM.ENABLE) {
            await sendTelegram(message);
            console.log('✅ 텔레그램 알림 발송 완료');
        } else {
            console.log('ℹ️ 텔레그램 알림 비활성 상태 (데이터만 저장)');
        }

        // 내역 저장
        const todayStr = new Date().toISOString().split('T')[0];
        try {
            const histEntry = {
                date: todayStr,
                stocks: top3.map(s => ({
                    code: s.code,
                    name: s.name,
                    buyPrice: s.price,
                    nextOpen: 0,
                    change: 0,
                    tradingValue: s.tradingValue,
                    score: s.score
                }))
            };
            let history = [];
            if (fs.existsSync(historyFilePath)) {
                history = JSON.parse(fs.readFileSync(historyFilePath, 'utf8'));
            }
            const idx = history.findIndex(h => h.date === todayStr);
            if (idx > -1) history[idx] = histEntry;
            else history.push(histEntry);
            fs.writeFileSync(historyFilePath, JSON.stringify(history, null, 2));
            console.log('✅ 오늘 추천 내역 저장 완료');
        } catch (e) {
            console.error('내역 저장 실패:', e);
        }
    } catch (error) {
        console.error('❌ 추천 종목 발송 실패:', error);
    }
}

async function updateHistoryGaps() {
    try {
        if (!fs.existsSync(historyFilePath)) return;
        let history = JSON.parse(fs.readFileSync(historyFilePath, 'utf8'));
        if (history.length === 0) return;

        const today = new Date().toISOString().split('T')[0];
        let modified = false;

        for (let dayEntry of history) {
            if (dayEntry.date === today) continue; // 오늘 데이터면 아직 시초가 모름

            for (let stock of dayEntry.stocks) {
                if (stock.nextOpen === 0) {
                    console.log(`🔍 [History] ${dayEntry.date} 추천주 ${stock.name} 시초가 누락 확인...`);

                    // 토큰 및 정보 조회
                    if (!await ensureValidToken()) continue;
                    const response = await fetch(`${getBaseUrl()}/api/dostk/stkinfo`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json;charset=UTF-8',
                            'Authorization': `Bearer ${accessToken}`,
                            'appkey': KIWOOM_CONFIG.APP_KEY,
                            'api-id': 'ka10001'
                        },
                        body: JSON.stringify({ stk_cd: stock.code })
                    });
                    const data = await response.json();

                    if (data.open_pric) {
                        const openPrice = Math.abs(parseInt(String(data.open_pric).replace(/[+,]/g, '')) || 0);
                        if (openPrice > 0) {
                            stock.nextOpen = openPrice;
                            stock.change = parseFloat(((openPrice - stock.buyPrice) / stock.buyPrice * 100).toFixed(2));
                            console.log(`✅ [History] ${stock.name} 시초가 업데이트: ${openPrice}원 (${stock.change}%)`);
                            modified = true;
                        }
                    }
                    await new Promise(r => setTimeout(r, 200)); // API 부하 방지
                }
            }
        }

        if (modified) {
            fs.writeFileSync(historyFilePath, JSON.stringify(history, null, 2));
        }
    } catch (e) {
        console.error('❌ 내역 업데이트 실패:', e);
    }
}

async function sendTelegram(text) {
    const { BOT_TOKEN, CHAT_ID } = UI_CONFIG.TELEGRAM;
    if (!BOT_TOKEN || BOT_TOKEN.includes('YOUR_')) {
        console.error('❌ 텔레그램 BOT_TOKEN이 설정되지 않았습니다.');
        return;
    }
    try {
        const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: CHAT_ID,
                text: text,
                parse_mode: 'Markdown'
            })
        });
        const data = await response.json();
        if (!data.ok) console.error('❌ 텔레gram API 오류:', data);
    } catch (error) {
        console.error('❌ 텔레그램 네트워크 오류:', error.message);
    }
}

// 추천 내역 조회
app.get('/api/history', (req, res) => {
    try {
        if (!fs.existsSync(historyFilePath)) return res.json([]);
        const data = fs.readFileSync(historyFilePath, 'utf8');
        res.json(JSON.parse(data));
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 네이버 금융 뉴스 크롤링 API
app.get('/api/news/:code', async (req, res) => {
    try {
        const stockCode = req.params.code;

        // 캐시 확인
        if (newsCache.has(stockCode)) {
            const cached = newsCache.get(stockCode);
            if (Date.now() - cached.timestamp < NEWS_CACHE_TTL) {
                return res.json({ success: true, data: cached.data });
            }
        }

        const url = `https://finance.naver.com/item/news_news.naver?code=${stockCode}`;
        console.log(`📰 뉴스 크롤링 요청: ${stockCode}`);

        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': `https://finance.naver.com/item/main.naver?code=${stockCode}`
            },
            responseType: 'arraybuffer',
            timeout: 5000
        });

        const iconv = require('iconv-lite');
        const content = iconv.decode(response.data, 'euc-kr');
        const $ = cheerio.load(content);

        const newsList = [];
        // 네이버 금융의 새로운/다양한 구조 대응 (type5 또는 관련 클래스)
        $('table.type5 tr, .tb_type_news tr').each((i, el) => {
            const titleEl = $(el).find('td.title a.tit, .titles a');
            if (titleEl.length > 0 && newsList.length < 8) {
                let title = titleEl.text().trim();
                let link = titleEl.attr('href') || '';

                if (link.startsWith('/')) {
                    link = 'https://finance.naver.com' + link;
                }

                const info = $(el).find('.info').text().trim();
                const date = $(el).find('.date').text().trim();

                // 중복 제목 및 무의미한 데이터 필터링
                if (title && !newsList.find(n => n.title === title)) {
                    newsList.push({ title, link, info, date });
                }
            }
        });

        // 결과 캐싱
        newsCache.set(stockCode, { data: newsList, timestamp: Date.now() });

        res.json({ success: true, data: newsList });
    } catch (error) {
        console.error('뉴스 크롤링 오류:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// 추천 내역 수동 저장
app.post('/api/history', (req, res) => {
    try {
        const newEntry = req.body;
        let history = [];
        if (fs.existsSync(historyFilePath)) {
            history = JSON.parse(fs.readFileSync(historyFilePath, 'utf8'));
        }
        const index = history.findIndex(h => h.date === newEntry.date);
        if (index > -1) history[index] = newEntry;
        else history.push(newEntry);
        fs.writeFileSync(historyFilePath, JSON.stringify(history, null, 2), 'utf8');
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(PORT, '0.0.0.0', async () => {
    console.log(`
╔════════════════════════════════════════════════════╗
║   🚀 종가 베팅 대시보드 서버 (키움증권 REST API)   ║
╠════════════════════════════════════════════════════╣
║  🌐 URL: http://localhost:3005                     ║
║  📡 API: ${KIWOOM_CONFIG.REAL_SERVER}           ║
╚════════════════════════════════════════════════════╝
    `);

    // 시작 시 토큰 발급 및 누락된 내역 업데이트 시도 (비동기 수행하여 서버 시작 방해 금지)
    getAccessToken().then(() => {
        updateHistoryGaps().then(() => {
            console.log('✅ 초기 백그라운드 작업 완료');
        });
    });

    // ⏰ 추천 종목 생성 및 내역 관리 스케줄러
    let lastSentDate = '';
    setInterval(async () => {
        if (!UI_CONFIG || !UI_CONFIG.TELEGRAM) return;

        const now = new Date();
        const today = now.toISOString().split('T')[0];
        const currentTime = now.toTimeString().substring(0, 5); // "HH:mm"

        // 1. 설정된 추천 시간 (15:20)에 추천 생성 및 저장
        if (currentTime === UI_CONFIG.TELEGRAM.SEND_TIME && lastSentDate !== today) {
            const day = now.getDay();
            if (day >= 1 && day <= 5) { // 평일만 실행
                console.log(`🎯 [${currentTime}] 오늘의 추천 종목 생성 및 내역 저장 시작...`);
                lastSentDate = today;
                await sendTopRecommendationsToTelegram();
            }
        }

        // 2. 주기적으로 누락된 시초가 업데이트 (오전 9시 이후 등)
        if (currentTime === '09:05' || currentTime === '10:00' || currentTime === '13:00') {
            await updateHistoryGaps();
        }
    }, 60000);

    console.log('⏰ 알림 및 데이터 저장 스케줄러 활성화 (15:30 KST)');
});
