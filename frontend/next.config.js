/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Docker standalone 출력용 설정
  output: 'standalone',

  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:5111';

    return [
      // API 요청을 백엔드로 포워딩
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
