/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { proxyTimeout: 600000 },
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/:path*` }];
  },
};
module.exports = nextConfig;



