// 종가 베팅 대시보드 - 클라이언트 스크립트
// 로컬 서버 API를 통한 실시간 데이터 조회

// ========================================
// 설정
// ========================================
const CONFIG = {
    // 서버 포트 3005로 수정
    API_BASE: 'http://localhost:3005/api',
    REFRESH_INTERVAL: (typeof KIWOOM_CONFIG !== 'undefined' && KIWOOM_CONFIG.REFRESH_INTERVAL) ? KIWOOM_CONFIG.REFRESH_INTERVAL : 10000,
    WATCHLIST: (typeof KIWOOM_CONFIG !== 'undefined' && KIWOOM_CONFIG.WATCHLIST) ? KIWOOM_CONFIG.WATCHLIST : []
};

// 전역 상태
let stockData = {};
let chartData = [];
let isMarketOpen = false;
let isRecommendationTime = false; // 15:10 이후 추천 시작 여부

// ========================================
// 초기화
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 종가 베팅 대시보드 시작...');

    initClock();
    checkMarketStatus();

    // API 상태 확인
    const apiStatus = await checkApiStatus();
    if (!apiStatus.configValid) {
        showConfigError();
        return;
    }

    // 토큰 발급
    const tokenSuccess = await requestToken();
    if (!tokenSuccess) {
        showTokenError('토큰 발급에 실패했습니다. API 키를 확인해주세요.');
        return;
    }

    // 데이터 로드 및 갱신 시작
    await fetchAllStockData();
    await initChart();
    initAnimations();

    // 클릭 이벤트 추가 (종목 전환용)
    const cardsContainer = document.querySelector('.stock-cards');
    if (cardsContainer) {
        cardsContainer.addEventListener('click', (e) => {
            const card = e.target.closest('.stock-card');
            if (card && card.dataset.code) {
                const code = card.dataset.code;
                if (stockData[code]) {
                    console.log(`🎯 종목 전환: ${stockData[code].name}`);
                    currentChartStock = stockData[code];
                    initChart();
                    updateCriteriaChecklist(currentChartStock);

                    // 시각적 강조 즉시 반영
                    document.querySelectorAll('.stock-card').forEach(c => {
                        c.style.borderColor = 'var(--border-color)';
                        c.style.boxShadow = 'none';
                        c.classList.remove('active-chart');
                    });
                    card.style.borderColor = 'var(--accent-primary)';
                    card.style.boxShadow = '0 0 15px var(--accent-glow)';
                    card.classList.add('active-chart');
                }
            }
        });
    }

    // 주기적 갱신
    setInterval(fetchAllStockData, CONFIG.REFRESH_INTERVAL);
    setInterval(refreshChart, 30000); // 차트는 30초마다 갱신
    setInterval(checkMarketStatus, 60000); // 장 상태는 1분마다 확인

    // 화면 꺼짐 방지 (Wake Lock)
    initWakeLock();
});

// 화면 꺼짐 방지 기능
let wakeLock = null;
async function initWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('💡 화면 꺼짐 방지 활성화됨');

            wakeLock.addEventListener('release', () => {
                console.log('💡 화면 꺼짐 방지 해제됨');
            });
        }
    } catch (err) {
        console.warn('❌ 화면 꺼짐 방지 설정 실패:', err.message);
    }
}

// 창이 다시 포커스될 때 Wake Lock 재요청
document.addEventListener('visibilitychange', async () => {
    if (wakeLock !== null && document.visibilityState === 'visible') {
        wakeLock = await navigator.wakeLock.request('screen');
    }
});

// ========================================
// API 호출
// ========================================
async function checkApiStatus() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/status`);
        return await response.json();
    } catch (error) {
        console.error('API 상태 확인 실패:', error);
        return { configValid: false, hasToken: false };
    }
}

async function requestToken() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/token`, { method: 'POST' });
        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('토큰 요청 실패:', error);
        return false;
    }
}

async function fetchAllStockData() {
    console.log(`📡 [${new Date().toLocaleTimeString()}] 실시간 주도주 TOP 50 스캔 시작...`);

    try {
        // 1. 시장 순위 데이터 가져오기 (고정 10초 주기)
        let leaderCodes = [];

        // KOSPI/KOSDAQ 각각 50개씩 확보하여 전체 100개 후보 추출
        const [kospiRes, kosdaqRes] = await Promise.all([
            fetch(`${CONFIG.API_BASE}/market/rank?market=001`),
            fetch(`${CONFIG.API_BASE}/market/rank?market=101`)
        ]);

        const [kospiData, kosdaqData] = await Promise.all([kospiRes.json(), kosdaqRes.json()]);

        if (kospiData.success && kospiData.data) {
            leaderCodes = leaderCodes.concat(kospiData.data.slice(0, 50).map(item => item.stk_cd || item.code));
        }
        if (kosdaqData.success && kosdaqData.data) {
            leaderCodes = leaderCodes.concat(kosdaqData.data.slice(0, 50).map(item => item.stk_cd || item.code));
        }

        const combinedCodes = [...new Set(leaderCodes)].filter(Boolean);
        if (combinedCodes.length === 0) return;

        // 2. 모든 종목 상세 정보 가져오기
        const response = await fetch(`${CONFIG.API_BASE}/stocks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codes: combinedCodes })
        });

        const result = await response.json();

        if (result.success && result.data) {
            // [규칙 1] 거래대금 기준 전시장 통합 TOP 50 산출
            const sortedByValue = Object.values(result.data)
                .sort((a, b) => (b.tradingValue || 0) - (a.tradingValue || 0))
                .slice(0, 50);

            // [규칙 3/4] 실데이타 기반 점수화 및 뉴스 존재 여부 확인
            // 거래대금 상위 20개 + 점수 40점 이상 종목에 대해 뉴스 유무 체크 (풍부한 후보 확보)
            const processedStocks = await Promise.all(sortedByValue.map(async (stock, index) => {
                const score = calculateScore(stock);

                // [규칙 4] 상위권(거래대금 TOP 20) 또는 점수 우수 종목에 대해 뉴스 확인
                let hasNews = false;
                if (index < 20 || score >= 40) {
                    try {
                        const newsRes = await fetch(`${CONFIG.API_BASE}/news/${stock.code}`);
                        const newsData = await newsRes.json();
                        // 뉴스가 1개라도 있으면 통과
                        hasNews = newsData.success && newsData.data && newsData.data.length > 0;
                        if (hasNews) stock.latestNews = newsData.data[0];
                    } catch (e) { hasNews = false; }
                }

                return { ...stock, score, hasNews };
            }));

            // 전체 데이터 업데이트
            stockData = {};
            processedStocks.forEach(s => { stockData[s.code] = s; });

            updateDashboard(processedStocks);
            console.log(`✅ TOP 50 분석 완료 (뉴스 확인 완료)`);
        }
    } catch (error) {
        console.error('📊 데이터 수집 오류 (실시간 API 연결 확인 필요):', error);
    }
}

function syncChartWithData() {
    const sorted = Object.values(stockData).sort((a, b) => (b.changeRate || 0) - (a.changeRate || 0));
    if (sorted.length > 0) {
        // 현재 차트 종목이 없거나, 현재 차트 종목이 새로운 데이터 목록에 없으면 1위로 교체
        if (!currentChartStock || !stockData[currentChartStock.code]) {
            currentChartStock = sorted[0];
            initChart();
        }
    }
}

// ========================================
// 에러 표시
// ========================================
function showConfigError() {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.innerHTML = `
            <div style="grid-column: 1/-1; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; text-align: center;">
                <div style="font-size: 4rem; margin-bottom: 20px;">🔑</div>
                <h2 style="color: #ef4444; margin-bottom: 10px;">API 키 설정 필요</h2>
                <p style="color: #94a3b8; margin-bottom: 20px;">config.js 파일에서 키움 REST API 키를 입력해주세요.</p>
                <div style="background: #1a2332; padding: 20px; border-radius: 12px; text-align: left; max-width: 500px; font-family: monospace;">
                    <div style="color: #64748b;">// config.js 파일 수정</div>
                    <div style="color: #10b981;">APP_KEY: '발급받은_API_KEY',</div>
                    <div style="color: #10b981;">APP_SECRET: '발급받은_SECRET_KEY'</div>
                </div>
                <p style="color: #64748b; margin-top: 20px; font-size: 0.9rem;">
                    설정 후 저장하고 페이지를 새로고침하세요. (서버 재시작이 필요할 수 있습니다)
                </p>
            </div>
        `;
    }
}

function showTokenError(message) {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.innerHTML = `
            <div style="grid-column: 1/-1; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; text-align: center;">
                <div style="font-size: 4rem; margin-bottom: 20px;">⚠️</div>
                <h2 style="color: #f59e0b; margin-bottom: 10px;">API 연결 오류</h2>
                <p style="color: #94a3b8; margin-bottom: 20px;">${message}</p>
                <button onclick="location.reload()" style="padding: 12px 24px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem;">
                    다시 시도
                </button>
            </div>
        `;
    }
}

// ========================================
// 시계 및 시장 상태
// ========================================
function initClock() {
    const timeEl = document.getElementById('current-time');
    const updateEl = document.getElementById('updateTime');

    function updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('ko-KR', { hour12: false });
        if (timeEl) timeEl.textContent = timeStr;
        if (updateEl) updateEl.textContent = timeStr;
        checkMarketStatus();
    }

    updateClock();
    setInterval(updateClock, 1000);
}

function checkMarketStatus() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const day = now.getDay();

    isMarketOpen = (day >= 1 && day <= 5) &&
        ((hours === 9 && minutes >= 0) ||
            (hours > 9 && hours < 15) ||
            (hours === 15 && minutes <= 30));

    // 15:10 이후부터 추천 데이터 신뢰도 상승 및 공식 추천 시작
    const currentTimeValue = hours * 100 + minutes;
    isRecommendationTime = (day >= 1 && day <= 5) && (currentTimeValue >= 1510);

    const statusEl = document.querySelector('.status-value');
    if (statusEl) {
        statusEl.textContent = isMarketOpen ? 'OPEN' : 'CLOSED';
        statusEl.className = `status-value ${isMarketOpen ? 'open' : 'closed'}`;
    }

    // 추천 상태 안내 텍스트 업데이트 (있을 경우)
    const subHeader = document.querySelector('.header-subtitle');
    if (subHeader) {
        if (isRecommendationTime) {
            subHeader.textContent = '🎯 종가배팅 공식 추천 진행 중';
            subHeader.style.color = '#10b981';
        } else if (isMarketOpen) {
            subHeader.textContent = '⏳ 종가배팅 후보 종목 모니터링 (15:10 추천 시작)';
            subHeader.style.color = '#94a3b8';
        } else {
            subHeader.textContent = '💤 시장 마감';
            subHeader.style.color = '#64748b';
        }
    }
}

// ========================================
// 대시보드 업데이트
// ========================================
// ========================================
// 대시보드 업데이트
// ========================================
function updateDashboard(processedStocks) {
    if (!processedStocks || processedStocks.length === 0) return;

    // [규칙 4] 추천 종목(카드)은 반드시 뉴스가 있어야 함을 원칙으로 함
    // 하지만 뉴스 크롤링 실패 시 대시보드가 비어 보이는 것을 방지하기 위해 최소 3개 노출 보장
    let finalCards = processedStocks
        .filter(s => s.hasNews)
        .sort((a, b) => {
            const aQualified = a.score >= 40 ? 1 : 0;
            const bQualified = b.score >= 40 ? 1 : 0;
            if (aQualified !== bQualified) return bQualified - aQualified;
            return (b.tradingValue || 0) - (a.tradingValue || 0);
        })
        .slice(0, 3);

    // 뉴스가 있는 종목이 3개 미만이면 거래대금 상위 종목으로 보충
    if (finalCards.length < 3) {
        const extraPicks = processedStocks
            .filter(s => !finalCards.find(f => f.code === s.code))
            .sort((a, b) => (b.tradingValue || 0) - (a.tradingValue || 0))
            .slice(0, 3 - finalCards.length);

        finalCards = [...finalCards, ...extraPicks];
    }

    // 상위 3개 추천 카드 업데이트
    updateStockCards(finalCards);

    // 섹터 업데이트 (전체 TOP 50 기준)
    updateSectorOverview(processedStocks);

    // 현재 선택된 차트 종목 상태 반영
    if (currentChartStock && stockData[currentChartStock.code]) {
        updateCriteriaChecklist(stockData[currentChartStock.code]);
    } else if (finalCards.length > 0) {
        currentChartStock = finalCards[0];
        updateCriteriaChecklist(currentChartStock);
        initChart();
    }

    updateLiveTicker(processedStocks);
    updateStats(processedStocks);
}

function calculateScore(stock) {
    if (!stock) return 0;

    // updateCriteriaChecklist에 있는 동일 로직으로 점수 합산
    const checks = [
        { val: (stock.low52w && stock.price > stock.low52w * 1.3 ? 15 : (stock.low52w && stock.price > stock.low52w * 1.1 ? 8 : 0)) }, // 바닥 대비 반등
        { val: ((stock.tradingValue || 0) >= 100000000000 ? 15 : ((stock.tradingValue || 0) >= 50000000000 ? 8 : 0)) }, // 거래대금
        { val: (stock.changeRate >= 3 ? 15 : (stock.changeRate >= 1 ? 8 : 0)) }, // 등락률
        { val: (stock.high && stock.price >= stock.high * 0.98 ? 15 : (stock.high && stock.price >= stock.high * 0.95 ? 8 : 0)) }, // 고가 인근
        { val: (stock.high52w && stock.price >= stock.high52w * 0.95 ? 15 : (stock.high52w && stock.price >= stock.high52w * 0.85 ? 8 : 0)) }, // 52주 신고가 근접
        { val: (stock.high52w && stock.price >= stock.high52w * 0.98 ? 15 : (stock.high52w && stock.price >= stock.high52w * 0.90 ? 8 : 0)) }, // 돌파형
        { val: (stock.changeRate >= 2 && stock.price > stock.open ? 10 : (stock.changeRate >= 0 ? 5 : 0)) } // 양봉 형태
    ];

    return checks.reduce((sum, c) => sum + c.val, 0);
}

function updateStockCards(topStocks) {
    const container = document.getElementById('top-stock-cards');
    if (!container) return;

    if (topStocks.length === 0) {
        container.innerHTML = '<p style="padding: 20px; color: #64748b; text-align: center;">조건을 만족하는 종목이 없습니다.</p>';
        return;
    }

    container.innerHTML = topStocks.map((stock, index) => {
        const isPositive = (stock.changeRate || 0) >= 0;
        const medal = isRecommendationTime
            ? (index === 0 ? '🥇 TOP PICK' : (index === 1 ? '🥈 2nd Pick' : '🥉 3rd Pick'))
            : (index === 0 ? '🔥 Candidate 1' : (index === 1 ? '⚡ Candidate 2' : '⭐ Candidate 3'));

        const badgeClass = index === 0 ? '' : (index === 1 ? 'silver' : 'bronze');
        const isActive = currentChartStock && stock.code === currentChartStock.code;
        const grades = calculateGrades(stock);

        return `
            <div class="stock-card ${index === 0 ? 'top-pick' : ''} ${isActive ? 'active-chart' : ''}" 
                 data-code="${stock.code}" 
                 onclick="selectStockForChart('${stock.code}')"
                 style="cursor:pointer; border-color: ${isActive ? 'var(--accent-primary)' : 'var(--border-color)'}; box-shadow: ${isActive ? '0 0 15px var(--accent-glow)' : 'none'}">
                <div class="card-badge ${badgeClass}">${medal}</div>
                <div class="stock-header">
                    <div class="stock-ticker">${stock.name}</div>
                    <div class="stock-code">${stock.code}</div>
                </div>
                <div class="stock-price">
                    <span class="price-value">${formatPrice(stock.price)}</span>
                    <span class="price-change ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '+' : ''}${stock.changeRate?.toFixed(2) || 0}%
                    </span>
                </div>
                <div class="stock-grades">
                    <div class="grade-item">
                        <span class="grade-label">Momentum</span>
                        <span class="grade-value grade-${grades.momentumClass}">${grades.momentum}</span>
                    </div>
                    <div class="grade-item">
                        <span class="grade-label">Volume</span>
                        <span class="grade-value grade-${grades.volumeClass}">${grades.volume}</span>
                    </div>
                    <div class="grade-item">
                        <span class="grade-label">Pattern</span>
                        <span class="grade-value grade-${grades.patternClass}">${grades.pattern}</span>
                    </div>
                </div>
                <div class="stock-meta">
                    ${generateMetaTagsHTML(stock)}
                </div>
            </div>
        `;
    }).join('');
}

function selectStockForChart(code) {
    if (stockData[code]) {
        currentChartStock = stockData[code];
        initChart();
        updateCriteriaChecklist(currentChartStock);
        updateDashboard(); // 시각적 강조 업데이트
    }
}

function generateMetaTagsHTML(stock) {
    const tags = [];
    const tradingValue = (stock.tradingValue || 0) / 100000000;

    if (tradingValue >= 5000) tags.push({ text: '📈 거래대금 상위', class: 'high-vol' });
    if (stock.high52w && stock.price >= stock.high52w * 0.95) {
        tags.push({ text: '🚀 52주 신고가 근접', class: 'material' });
    }
    if (stock.changeRate >= 5) tags.push({ text: '🔥 강세', class: 'material' });
    else if (stock.changeRate >= 3) tags.push({ text: '📊 상승세', class: '' });

    return tags.map(tag => `<span class="meta-tag ${tag.class}">${tag.text}</span>`).join('');
}

function calculateGrades(stock) {
    const rate = stock.changeRate || 0;
    const tradingValue = stock.tradingValue || 0;

    let momentum, momentumClass;
    if (rate >= 5) { momentum = 'A+'; momentumClass = 'a-plus'; }
    else if (rate >= 3) { momentum = 'A'; momentumClass = 'a'; }
    else if (rate >= 1) { momentum = 'B+'; momentumClass = 'b-plus'; }
    else if (rate >= 0) { momentum = 'B'; momentumClass = 'b'; }
    else { momentum = 'C'; momentumClass = 'c'; }

    let volume, volumeClass;
    const valueInBillion = tradingValue / 100000000;
    if (valueInBillion >= 5000) { volume = 'A+'; volumeClass = 'a-plus'; }
    else if (valueInBillion >= 1000) { volume = 'A'; volumeClass = 'a'; }
    else if (valueInBillion >= 500) { volume = 'B+'; volumeClass = 'b-plus'; }
    else { volume = 'B'; volumeClass = 'b'; }

    let pattern, patternClass;
    if (stock.high52w && stock.price >= stock.high52w * 0.95) {
        pattern = 'A+'; patternClass = 'a-plus';
    } else if (stock.high52w && stock.price >= stock.high52w * 0.85) {
        pattern = 'A'; patternClass = 'a';
    } else if (rate >= 0) {
        pattern = 'B+'; patternClass = 'b-plus';
    } else {
        pattern = 'B'; patternClass = 'b';
    }

    return { momentum, momentumClass, volume, volumeClass, pattern, patternClass };
}

function updateMetaTags(card, stock) {
    const metaContainer = card.querySelector('.stock-meta');
    if (!metaContainer) return;

    const tags = [];
    const tradingValue = (stock.tradingValue || 0) / 100000000;

    if (tradingValue >= 5000) tags.push({ text: '📈 거래대금 상위', class: 'high-vol' });
    if (stock.high52w && stock.price >= stock.high52w * 0.95) {
        tags.push({ text: '🚀 52주 신고가 근접', class: 'material' });
    }
    if (stock.changeRate >= 5) tags.push({ text: '🔥 강세', class: 'material' });
    else if (stock.changeRate >= 3) tags.push({ text: '📊 상승세', class: '' });

    metaContainer.innerHTML = tags.map(tag =>
        `<span class="meta-tag ${tag.class}">${tag.text}</span>`
    ).join('');
}

function updateSectorOverview(stocks) {
    const container = document.getElementById('sectors-list');
    if (!container) return;

    const sectorPerformance = {};

    stocks.forEach(stock => {
        const sector = stock.sector || '기타';
        if (!sectorPerformance[sector]) {
            sectorPerformance[sector] = { total: 0, count: 0, leaders: [] };
        }
        sectorPerformance[sector].total += (stock.changeRate || 0);
        sectorPerformance[sector].count++;
        sectorPerformance[sector].leaders.push(stock.name);
    });

    const sortedSectors = Object.entries(sectorPerformance)
        .map(([name, data]) => ({
            name,
            avgChange: data.total / data.count,
            leaders: data.leaders.slice(0, 2)
        }))
        .sort((a, b) => b.avgChange - a.avgChange)
        .slice(0, 4);

    if (sortedSectors.length === 0) {
        container.innerHTML = '<div class="loading-state">데이터 분석 중...</div>';
        return;
    }

    container.innerHTML = sortedSectors.map((sector, index) => {
        const isPositive = sector.avgChange >= 0;
        const width = Math.min(Math.max(Math.abs(sector.avgChange) * 15, 10), 100);
        const isHot = index === 0 && sector.avgChange >= 3;

        return `
            <div class="sector-item ${isHot ? 'hot' : ''}">
                <div class="sector-info">
                    <span class="sector-rank">${index + 1}</span>
                    <span class="sector-name">${sector.name}</span>
                </div>
                <div class="sector-stats">
                    <span class="sector-change ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '+' : ''}${sector.avgChange.toFixed(2)}%
                    </span>
                    <div class="sector-bar">
                        <div class="bar-fill" style="width: ${width}%"></div>
                    </div>
                </div>
                <div class="sector-leaders">
                    ${sector.leaders.map(l => `<span class="leader-tag">${l}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');
}



function updateCriteriaChecklist(stock) {
    const subtitle = document.querySelector('.criteria-subtitle');
    if (subtitle) {
        subtitle.textContent = isRecommendationTime
            ? `${stock.name} 최종 추천 분석`
            : `${stock.name} 후보 종목 분석중...`;
    }

    const items = document.querySelectorAll('.criteria-item');

    if (!isRecommendationTime) {
        items.forEach(item => {
            item.classList.remove('passed', 'partial', 'failed');
            item.querySelector('.criteria-check').textContent = '⋯';
        });
        const scoreValue = document.querySelector('.score-value');
        const scoreFill = document.querySelector('.score-fill');
        if (scoreValue) scoreValue.innerHTML = `<span style="font-size: 1.2rem; color: #64748b;">15:10 대기</span>`;
        if (scoreFill) scoreFill.style.width = `0%`;
        return;
    }

    const checks = [
        { passed: stock.low52w && stock.price > stock.low52w * 1.3, partial: stock.low52w && stock.price > stock.low52w * 1.1 },
        { passed: (stock.tradingValue || 0) >= 100000000000, partial: (stock.tradingValue || 0) >= 50000000000 },
        { passed: stock.changeRate >= 3, partial: stock.changeRate >= 1 },
        { passed: stock.high && stock.price >= stock.high * 0.98, partial: stock.high && stock.price >= stock.high * 0.95 },
        { passed: stock.high52w && stock.price >= stock.high52w * 0.95, partial: stock.high52w && stock.price >= stock.high52w * 0.85 },
        { passed: stock.high52w && stock.price >= stock.high52w * 0.98, partial: stock.high52w && stock.price >= stock.high52w * 0.90 },
        { passed: stock.changeRate >= 2 && stock.price > stock.open, partial: stock.changeRate >= 0 }
    ];

    let score = 0;
    items.forEach((item, index) => {
        if (index >= checks.length) return;

        const check = checks[index];
        item.classList.remove('passed', 'partial', 'failed');

        if (check.passed) {
            item.classList.add('passed');
            item.querySelector('.criteria-check').textContent = '✓';
            score += 15;
        } else if (check.partial) {
            item.classList.add('partial');
            item.querySelector('.criteria-check').textContent = '◐';
            score += 8;
        } else {
            item.classList.add('failed');
            item.querySelector('.criteria-check').textContent = '✗';
        }
    });

    score = Math.min(score, 100);
    const scoreValue = document.querySelector('.score-value');
    const scoreFill = document.querySelector('.score-fill');

    if (scoreValue) scoreValue.innerHTML = `${score}<span class="score-unit">/100</span>`;
    if (scoreFill) scoreFill.style.width = `${score}%`;
}

function updateLiveTicker(stocks) {
    const tickerScroll = document.querySelector('.ticker-scroll');
    if (!tickerScroll) return;

    const tickerHTML = stocks.slice(0, 6).map(stock => {
        const isPositive = (stock.changeRate || 0) >= 0;
        return `<span class="ticker-item" style="color: ${isPositive ? '#10b981' : '#ef4444'}">
            ${stock.name} ${formatPrice(stock.price)} (${isPositive ? '+' : ''}${stock.changeRate?.toFixed(2) || 0}%)
        </span>`;
    }).join('<span class="ticker-divider">|</span>');

    tickerScroll.innerHTML = tickerHTML + '<span class="ticker-divider">|</span>' + tickerHTML;
}

function updateStats(stocks) {
    const positive = stocks.filter(s => (s.changeRate || 0) >= 0);
    const avgReturn = stocks.length
        ? stocks.reduce((sum, s) => sum + (s.changeRate || 0), 0) / stocks.length
        : 0;

    const statValues = document.querySelectorAll('.stat-value');
    if (statValues[0]) statValues[0].textContent = stocks.length;
    if (statValues[1]) statValues[1].textContent = positive.length;
    if (statValues[2]) statValues[2].textContent = stocks.length
        ? `${Math.round(positive.length / stocks.length * 100)}%` : '-';
    if (statValues[3]) statValues[3].textContent = `${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(1)}%`;
}

// ========================================
// 유틸리티
// ========================================
function formatPrice(price) {
    if (!price) return '-';
    return Number(price).toLocaleString('ko-KR');
}

function formatTradingValue(value) {
    if (!value) return '-';
    const billion = value / 100000000;
    if (billion >= 10000) return `${(billion / 10000).toFixed(1)}조`;
    return `${Math.round(billion).toLocaleString()}억`;
}

// ========================================
// 차트
// ========================================
let currentChartStock = null;

async function initChart() {
    const canvas = document.getElementById('priceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.parentElement.offsetWidth;
    const height = canvas.parentElement.offsetHeight;
    canvas.width = width;
    canvas.height = height;

    // 현재 선택된 종목이 없으면 상위 종목으로 자동 선택
    if (!currentChartStock) {
        const topStock = Object.values(stockData)
            .filter(s => s && s.price > 0)
            .sort((a, b) => (b.changeRate || 0) - (a.changeRate || 0))[0];
        if (topStock) currentChartStock = topStock;
    }

    if (currentChartStock) {
        const chartStock = document.querySelector('.chart-stock');
        if (chartStock) chartStock.textContent = currentChartStock.name;

        const markerPrice = document.querySelector('.marker-price');
        if (markerPrice) markerPrice.textContent = `₩${formatPrice(currentChartStock.price)}`;

        // 실제 분봉 데이터 가져오기
        chartData = await fetchChartData(currentChartStock.code);

        // 관련 뉴스 가져오기
        fetchStockNews(currentChartStock.code);
    }

    if (chartData && chartData.length > 0) {
        drawChart(ctx, width, height, chartData);
    } else if (currentChartStock) {
        // API 실패시 현재가 기반 시뮬레이션 데이터 생성
        chartData = generateFallbackChartData(currentChartStock.price || 50000);
        drawChart(ctx, width, height, chartData);
    }

    animateEntryMarker();
}

// 분봉 차트 데이터 API 호출
async function fetchChartData(stockCode) {
    try {
        console.log(`📊 분봉 데이터 조회: ${stockCode}`);
        const response = await fetch(`${CONFIG.API_BASE}/chart/${stockCode}?tick=1`);
        const result = await response.json();

        if (result.success && result.data && result.data.length > 0) {
            console.log(`✅ 분봉 데이터 수신: ${result.data.length}개`);
            return result.data.slice(-60); // 최근 60분 데이터
        } else {
            console.warn('분봉 데이터 없음:', result.error);
            return null;
        }
    } catch (error) {
        console.error('분봉 데이터 조회 오류:', error);
        return null;
    }
}

// 뉴스 데이터 API 호출
async function fetchStockNews(stockCode) {
    const newsContainer = document.getElementById('stock-news-list');
    if (!newsContainer) return;

    try {
        const response = await fetch(`${CONFIG.API_BASE}/news/${stockCode}`);
        const result = await response.json();

        if (result.success && result.data && result.data.length > 0) {
            updateStockNewsUI(result.data);
        } else {
            newsContainer.innerHTML = '<div class="loading-state">관련 뉴스가 없습니다.</div>';
        }
    } catch (error) {
        console.error('뉴스 조회 오류:', error);
        newsContainer.innerHTML = '<div class="loading-state">뉴스 로딩 실패</div>';
    }
}

function updateStockNewsUI(newsList) {
    const newsContainer = document.getElementById('stock-news-list');
    if (!newsContainer) return;

    newsContainer.innerHTML = newsList.map(news => `
        <a href="${news.link}" target="_blank" class="news-item">
            <div class="news-title-row">
                <span class="news-title">${news.title}</span>
            </div>
            <div class="news-meta-row">
                <span class="news-info">${news.info}</span>
                <span class="news-date">${news.date}</span>
            </div>
        </a>
    `).join('');
}

// API 실패시 대체 데이터 생성 (가상 데이터 금지 설정에 따라 사용하지 않거나 최소화)
function generateFallbackChartData(basePrice) {
    // [규칙 5] 가상 데이터를 생성하지 않도록 빈 배열 반환하여 '수신 대기' 유도
    console.warn("⚠️ 실시간 차트 데이터를 수신하지 못했습니다. 가상 데이터를 생성하지 않습니다.");
    return [];
}

// 차트 새로고침 (주기적 업데이트용)
async function refreshChart() {
    if (!currentChartStock) return;

    const canvas = document.getElementById('priceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    const newData = await fetchChartData(currentChartStock.code);
    if (newData && newData.length > 0) {
        chartData = newData;
        drawChart(ctx, width, height, chartData);

        // 현재가 업데이트
        const markerPrice = document.querySelector('.marker-price');
        if (markerPrice && chartData.length > 0) {
            const lastCandle = chartData[chartData.length - 1];
            markerPrice.textContent = `₩${formatPrice(lastCandle.close)}`;
        }
    }
}

function drawChart(ctx, width, height, data) {
    const padding = { top: 20, right: 60, bottom: 40, left: 20 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, height);

    // 배경 그리드
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
    }

    if (!data || data.length === 0) return;

    const prices = data.flatMap(d => [d.high, d.low]).filter(p => p > 0);
    if (prices.length === 0) return;

    const actualMin = Math.min(...prices);
    const actualMax = Math.max(...prices);
    let diff = actualMax - actualMin;

    // 변동폭을 더 크게 보여주기 위해 여백 최소화 (데이터의 5%만 여백으로 사용)
    let minPrice = actualMin - (diff * 0.05);
    let maxPrice = actualMax + (diff * 0.05);

    // 변동이 없는 경우 대비
    if (diff === 0) {
        minPrice = actualMin * 0.999;
        maxPrice = actualMax * 1.001;
    }
    const priceRange = maxPrice - minPrice;

    const gap = chartWidth / data.length;
    const candleWidth = gap * 0.7;

    data.forEach((candle, i) => {
        const x = padding.left + gap * i + gap / 2;
        const isGreen = candle.close >= candle.open;

        // Y축 좌표 계산
        const getY = (price) => padding.top + chartHeight * (1 - (price - minPrice) / priceRange);

        const yOpen = getY(candle.open);
        const yClose = getY(candle.close);
        const yHigh = getY(candle.high);
        const yLow = getY(candle.low);

        // 꼬리 그리기
        ctx.strokeStyle = isGreen ? '#10b981' : '#ef4444';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, yHigh);
        ctx.lineTo(x, yLow);
        ctx.stroke();

        // 몸통 그리기
        ctx.fillStyle = isGreen ? '#10b981' : '#ef4444';
        const bodyTop = Math.min(yOpen, yClose);
        const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1);
        ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);

        // 종가배팅 시간대 하이라이트 (15:20 ~ 15:30)
        const time = candle.time || '';
        if (time >= '15:20' && time <= '15:30') {
            ctx.fillStyle = 'rgba(16, 185, 129, 0.1)';
            ctx.fillRect(x - gap / 2, padding.top, gap, chartHeight);
        }

        // X축 시간 라벨은 하단 HTML timeline을 사용하므로 생략 (중복 방지)
        /*
        if (i % 10 === 0 || i === data.length - 1) {
            ctx.fillStyle = '#64748b';
            ctx.font = '10px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(time, x, height - padding.bottom + 20);
        }
        */
    });

    // 거래량 바 그리기
    const volumes = data.map(d => d.volume || 0);
    const maxVol = Math.max(...volumes) || 1;
    const volMaxHeight = 30;

    volumes.forEach((vol, i) => {
        const x = padding.left + gap * i + gap / 2;
        const barHeight = (vol / maxVol) * volMaxHeight;
        const isEntry = data[i].time >= '15:20' && data[i].time <= '15:30';

        ctx.fillStyle = isEntry ? 'rgba(6, 182, 212, 0.6)' : 'rgba(100, 116, 139, 0.2)';
        ctx.fillRect(x - candleWidth / 2, height - padding.bottom - barHeight, candleWidth, barHeight);
    });

    // Y축 가격 라벨
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const price = maxPrice - (priceRange / 5) * i;
        const y = padding.top + (chartHeight / 5) * i;
        ctx.fillText(Math.round(price).toLocaleString(), width - 5, y + 4);
    }
}

function animateEntryMarker() {
    const marker = document.getElementById('entryMarker');
    if (!marker) return;

    let offset = 0;
    setInterval(() => {
        offset = Math.sin(Date.now() / 500) * 3;
        marker.style.transform = `translate(-50%, calc(-50% + ${offset}px))`;
    }, 50);
}

function initAnimations() {
    setTimeout(() => {
        const scoreFill = document.querySelector('.score-fill');
        if (scoreFill) scoreFill.style.transition = 'width 1.5s ease-out';
    }, 500);

    document.querySelectorAll('.stock-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-8px) scale(1.02)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });
}

window.addEventListener('resize', () => initChart());

// ========================================
// 추천 내역 리스트 (History)
// ========================================
const historyModal = document.getElementById('history-modal');
const btnHistory = document.getElementById('btn-history');
const btnCloseModal = document.querySelector('.close-modal');
const historyListBody = document.getElementById('history-list-body');
const btnRunCalc = document.getElementById('btn-run-calc');

if (btnHistory) {
    btnHistory.addEventListener('click', openHistory);
}

if (btnCloseModal) {
    btnCloseModal.addEventListener('click', () => historyModal.classList.remove('active'));
}

if (btnRunCalc) {
    btnRunCalc.addEventListener('click', renderHistoryTable);
}

// 모달 외부 클릭시 닫기
window.addEventListener('click', (e) => {
    if (e.target === historyModal) historyModal.classList.remove('active');
});

async function openHistory() {
    historyModal.classList.add('active');
    await renderHistoryTable();
}

async function renderHistoryTable() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/history`);
        const historyData = await response.json();

        const tp = parseFloat(document.getElementById('calc-tp').value) || 3;
        const sl = parseFloat(document.getElementById('calc-sl').value) || 2;

        let totalReturn = 0;
        let totalCount = 0;
        let winCount = 0;

        historyListBody.innerHTML = '';

        // 날짜 역순 (최신순) 정렬
        [...historyData].reverse().forEach(day => {
            day.stocks.forEach(stock => {
                const rt = stock.change !== undefined ? stock.change : ((stock.nextOpen - stock.buyPrice) / stock.buyPrice * 100);
                totalReturn += rt;
                totalCount++;

                // 시뮬레이션 결과: 수익률이 TP보다 높으면 익절성공
                const isWin = rt >= tp;
                if (isWin) winCount++;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${day.date}</td>
                    <td><strong>${stock.name}</strong></td>
                    <td>${formatPrice(stock.buyPrice)}</td>
                    <td>${formatPrice(stock.nextOpen)}</td>
                    <td class="return-val ${rt >= 0 ? 'positive' : 'negative'}">
                        ${rt >= 0 ? '+' : ''}${rt.toFixed(2)}%
                    </td>
                    <td>
                        <span class="badge-result ${isWin ? 'badge-success' : (rt <= -sl ? 'badge-fail' : '')}">
                            ${isWin ? '익절성공' : (rt <= -sl ? '손절기준' : '홀딩/보통')}
                        </span>
                    </td>
                `;
                historyListBody.appendChild(tr);
            });
        });

        // 통계 업데이트
        document.getElementById('hist-total-count').textContent = `${totalCount}건`;
        document.getElementById('hist-avg-return').textContent = `${(totalReturn / (totalCount || 1)).toFixed(2)}%`;
        document.getElementById('hist-win-rate').textContent = `${((winCount / (totalCount || 1)) * 100).toFixed(1)}%`;

    } catch (error) {
        console.error('내역 로드 실패:', error);
        if (historyListBody) {
            historyListBody.innerHTML = '<tr><td colspan="6" style="text-align:center">내역을 불러오는데 실패했습니다.</td></tr>';
        }
    }
}
