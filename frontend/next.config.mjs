/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Docker standalone 출력용 설정
  output: 'standalone',

  // 빌드 시 ESLint 경고 무시 (pre-existing issues)
  eslint: {
    ignoreDuringBuilds: true,
  },

  // 프로덕션 환경에서 HMR WebSocket 비활성화
  webpack: (config, { dev, isServer }) => {
    // 프로덕션 빌드에서 HMR 관련 코드 제거
    if (!dev) {
      config.resolve.alias = {
        ...config.resolve.alias,
        'webpack/hot/poll': false,
      };
    }
    return config;
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

export default nextConfig;
