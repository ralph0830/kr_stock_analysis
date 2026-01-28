/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:5111';

    return [
      // API 요청을 백엔드로 포워딩
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      // WebSocket 연결을 백엔드로 포워딩 (WebSocket은 rewrites로 동작하지 않음)
      // Nginx Proxy Manager에서 별도 설정 필요
    ];
  },
};

module.exports = nextConfig;
