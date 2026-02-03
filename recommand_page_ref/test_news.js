const axios = require('axios');
const cheerio = require('cheerio');
const iconv = require('iconv-lite');

async function testNews(code) {
    try {
        const url = `https://finance.naver.com/item/news_news.naver?code=${code}`;
        console.log(`Testing news for ${code}...`);
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': `https://finance.naver.com/item/main.naver?code=${code}`
            },
            responseType: 'arraybuffer'
        });
        const content = iconv.decode(response.data, 'euc-kr');
        console.log('HTML Length:', content.length);
        const $ = cheerio.load(content);

        const newsList = [];
        $('table.type5 tr, .tb_type_news tr').each((i, el) => {
            const titleEl = $(el).find('td.title a.tit, .titles a');
            if (titleEl.length > 0) {
                const title = titleEl.text().trim();
                const link = titleEl.attr('href');
                console.log(`- [${i}] Title: ${title}`);
                newsList.push({ title, link });
            }
        });
        console.log('Total news found:', newsList.length);
    } catch (e) {
        console.error('Test failed:', e.message);
    }
}

testNews('005930');
