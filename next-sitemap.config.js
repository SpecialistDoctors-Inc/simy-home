module.exports = {
  siteUrl: "https://ai-mentor.app/",
  generateRobotsTxt: true,
  sitemapSize: 7000,
  outDir: "./public",
  trailingSlash: true,
  robotsTxtOptions: {
    policies: [
      {
        userAgent: "*",
        allow: "/",
      },
    ],
  },
  exclude: ["*"],
  additionalPaths: async (config) => {
    const res = [];

    // ホームページ
    res.push({
      loc: `https://ai-mentor.app/`,
      priority: 1.0,
      lastmod: new Date().toISOString(),
    });

    // Terms of Use ページ
    res.push({
      loc: `https://ai-mentor.app/terms.html`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
    });

    // Privacy Policy ページ
    res.push({
      loc: `https://ai-mentor.app/privacy.html`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
    });

    // Seller Information Disclosure ページ
    res.push({
      loc: `https://ai-mentor.app/seller-info.html`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
    });

    return res;
  },
};
