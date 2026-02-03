
const axios = require('axios');
const path = require('path');
const config = require('./config');

async function testKiwoomRank() {
    console.log("=== Kiwoom API Connection Test ===");

    // 1. Get Token
    try {
        const tokenRes = await axios.post('https://api.kiwoom.com/oauth2/token', {
            grant_type: 'client_credentials',
            appkey: config.APP_KEY,
            secretkey: config.APP_SECRET
        });

        const token = tokenRes.data.token || tokenRes.data.access_token;
        if (!token) {
            console.error("❌ Failed to get token:", tokenRes.data);
            return;
        }
        console.log("✅ Token received successfully.");

        // 2. Test Market Rank (KOSPI)
        console.log("📡 Requesting KOSPI Market Rank (ka10032)...");
        const rankRes = await axios.post('https://api.kiwoom.com/api/dostk/rkinfo', {
            mrkt_tp: '001',
            mang_stk_incls: '1',
            stex_tp: '1'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'appkey': config.APP_KEY,
                'api-id': 'ka10032'
            }
        });

        const items = rankRes.data.trde_prica_upper || rankRes.data.items || [];
        console.log(`✅ Received ${items.length} items from KOSPI.`);
        if (items.length > 0) {
            console.log("Top 5 KOSPI Codes:", items.slice(0, 5).map(i => i.stk_cd || i.code));
        }

        // 2-2. Test Market Rank (KOSDAQ)
        console.log("📡 Requesting KOSDAQ Market Rank (ka10032)...");
        const rankKdqRes = await axios.post('https://api.kiwoom.com/api/dostk/rkinfo', {
            mrkt_tp: '101',
            mang_stk_incls: '1',
            stex_tp: '1'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'appkey': config.APP_KEY,
                'api-id': 'ka10032'
            }
        });

        const kdqItems = rankKdqRes.data.trde_prica_upper || rankKdqRes.data.items || [];
        console.log(`✅ Received ${kdqItems.length} items from KOSDAQ.`);
        if (kdqItems.length > 0) {
            console.log("Top 5 KOSDAQ Codes:", kdqItems.slice(0, 5).map(i => i.stk_cd || i.code));
        }

        // 3. Test Individual Stock (SK Hynix: 000660)
        console.log("📡 Requesting SK Hynix (000660) Info (ka10001)...");
        const infoRes = await axios.post('https://api.kiwoom.com/api/dostk/stkinfo', {
            stk_cd: '000660'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'appkey': config.APP_KEY,
                'api-id': 'ka10001'
            }
        });

        console.log("✅ SK Hynix Data received:", JSON.stringify(infoRes.data).substring(0, 200));

        // 4. Test EchoPro (086520) Info (ka10001)
        console.log("📡 Requesting EchoPro (086520) Info (ka10001)...");
        const echoRes = await axios.post('https://api.kiwoom.com/api/dostk/stkinfo', {
            stk_cd: '086520'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'appkey': config.APP_KEY,
                'api-id': 'ka10001'
            }
        });

        console.log("✅ EchoPro Data received:", JSON.stringify(echoRes.data).substring(0, 200));

        const skValue = parseInt(infoRes.data.mac.replace(/[+,]/g, '')) * 1000000;
        const echoValue = parseInt(echoRes.data.mac.replace(/[+,]/g, '')) * 1000000;

        // 5. Test Samsung Electro-Mechanics (009150)
        console.log("📡 Requesting Samsung Electro-Mechanics (009150) Info (ka10001)...");
        const semRes = await axios.post('https://api.kiwoom.com/api/dostk/stkinfo', {
            stk_cd: '009150'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'appkey': config.APP_KEY,
                'api-id': 'ka10001'
            }
        });
        const semValue = parseInt(semRes.data.mac.replace(/[+,]/g, '')) * 1000000;

        console.log(`SK Hynix Trading Value: ${skValue.toLocaleString()} KRW`);
        console.log(`EchoPro Trading Value: ${echoValue.toLocaleString()} KRW`);
        console.log(`Samsung Electro-Mechanics Trading Value: ${semValue.toLocaleString()} KRW`);

        const list = [
            { name: 'SK Hynix', val: skValue },
            { name: 'EchoPro', val: echoValue },
            { name: 'Samsung Electro-Mechanics', val: semValue }
        ].sort((a, b) => b.val - a.val);

        console.log(`Higher: ${list[0].name}`);

    } catch (err) {
        console.error("❌ API Test Error:", err.response ? err.response.data : err.message);
    }
}

testKiwoomRank();
