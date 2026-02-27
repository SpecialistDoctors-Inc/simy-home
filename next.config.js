/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: false,
  images: {
    unoptimized: true,
    disableStaticImages: true,
    formats: ["image/webp"],
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          "source": "/test",
          "destination": "/test/index.html"
        },
        {
          "source": "/test/",
          "destination": "/test/index.html"
        }
      ],
      afterFiles: [
        {
          "source": "/.well-known/apple-app-site-association",
          "destination": "/.well-known/apple-app-site-association.json"
        }
      ]
    }
  },
  webpack: function (config) {
    config.module.rules.push({
      test: /\.md$/,
      use: "raw-loader",
    });
    config.module.rules.push({
      test: /\.svg$/,
      use: [
        {
          loader: "@svgr/webpack",
          options: {
            svgo: false, // 圧縮無効
          },
        },
      ],
    });
    return config;
  },
  // Removed exportPathMap as AASA/assetlinks files are not needed for this web app
  trailingSlash: true,
  staticPageGenerationTimeout: 60 * 3,
};

module.exports = nextConfig;
