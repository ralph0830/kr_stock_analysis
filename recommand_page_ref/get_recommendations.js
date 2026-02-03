const fetch = require('node-fetch');

async function getRecommendations() {
    try {
        const response = await fetch('http://localhost:3005/api/stocks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                codes: [
                    '005930', '000660', '373220', '207940', '005380',
                    '000270', '068270', '005490', '051910', '035420',
                    '035720', '006400', '105560', '055550', '000100',
                    '003670', '012330', '066570', '247540', '086520'
                ]
            })
        });
        const result = await response.json();
        const stocks = Object.values(result.data);

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
            .sort((a, b) => b.score - a.score || b.changeRate - a.changeRate)
            .slice(0, 3);

        console.log(JSON.stringify(top3, null, 2));
    } catch (e) {
        console.error(e);
    }
}

getRecommendations();
