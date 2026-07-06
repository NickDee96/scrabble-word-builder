/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a standalone server build (server.js) consumed by Dockerfile.frontend.
  output: 'standalone',

  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },

  // Proxy /api/* to the backend so the browser can use same-origin relative URLs
  // (no CORS needed). The destination is resolved on the Next.js server.
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
