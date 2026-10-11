/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  serverExternalPackages: ['snowflake-sdk'],
};

module.exports = nextConfig;
