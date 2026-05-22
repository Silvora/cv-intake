/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      {
        source: '/',
        destination: '/cv',
        permanent: true,
      },
    ];
  },
}

export default nextConfig
