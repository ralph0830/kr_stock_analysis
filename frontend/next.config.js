/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Docker standalone 출력용 설정
  output: 'standalone',

  // 빌드 시 ESLint 경고 무시 (pre-existing issues)
  eslint: {
    ignoreDuringBuilds: true,
  },

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
