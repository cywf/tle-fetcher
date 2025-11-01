/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/tle-fetcher',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  reactStrictMode: true,
}

module.exports = nextConfig
