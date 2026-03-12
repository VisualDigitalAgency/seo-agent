/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow larger response bodies for SSE streaming
  experimental: {
    serverActions: { bodySizeLimit: '10mb' }
  },
  // Ensure API routes don't timeout during long agent runs
  async headers() {
    return [
      {
        source: '/api/stream/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-cache, no-transform' },
          { key: 'X-Accel-Buffering', value: 'no' }
        ]
      }
    ]
  }
}

module.exports = nextConfig
