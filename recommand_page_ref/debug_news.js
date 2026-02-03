const axios = require('axios');
const iconv = require('iconv-lite');

async function debugHTML(code) {
    try {
        const url = `https://finance.naver.com/item/news_news.naver?code=${code}`;
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': `https://finance.naver.com/item/main.naver?code=${code}`
            },
            responseType: 'arraybuffer'
        });
        const content = iconv.decode(response.data, 'euc-kr');
        console.log(content);
    } catch (e) {
        console.error(e.message);
    }
}

debugHTML('005930');
