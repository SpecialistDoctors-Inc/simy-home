const locales = require("./src/components/locales.json");
const mathematics = require("./src/components/mathematics.json");
const localesNoEN = locales.filter((locale) => locale.value != "en");
const localesNoENJA = locales.filter(
  (locale) => locale.value != "en" && locale.value != "ja"
);

module.exports = {
  siteUrl: "https://www.ai-tutor.app/",
  generateRobotsTxt: true,
  sitemapSize: 7000,
  outDir: "./public",
  trailingSlash: true,
  robotsTxtOptions: {
    policies: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          ...localesNoEN.map(
            (localeMap) =>
              `/${localeMap.value.toLowerCase()}/products/homework/`
          ),
          ...localesNoENJA.map(
            (localeMap) => `/${localeMap.value.toLowerCase()}/cookie_policy/`
          ),
          ...localesNoENJA.map(
            (localeMap) => `/${localeMap.value.toLowerCase()}/privacy_policy/`
          ),
          ...localesNoENJA.map(
            (localeMap) => `/${localeMap.value.toLowerCase()}/terms/`
          ),
          ...localesNoENJA.map(
            (localeMap) => `/${localeMap.value.toLowerCase()}/trade/`
          ),
        ],
      },
    ],
  },
  exclude: ["*"],
  additionalPaths: async (config) => {
    const res = [];
    for (i in localesNoEN) {
      // localeページ
      res.push({
        loc: `https://www.ai-tutor.app/${localesNoEN[i].value.toLowerCase()}/`,
        priority: 0.8,
        lastmod: new Date().toISOString(),
        alternateRefs: [
          ...localesNoEN.map((locale) => {
            return {
              href: `https://www.ai-tutor.app/${locale.value.toLowerCase()}/`,
              hrefIsAbsolute: true,
              hreflang: locale.value,
            };
          }),
          {
            href: `https://www.ai-tutor.app/`,
            hrefIsAbsolute: true,
            hreflang: "en",
          },
        ],
      });

      // mathematicsページ
      for (j in mathematics.data) {
        for (k in mathematics.data[j].units) {
          for (l in mathematics.data[j].units[k].subunits) {
            res.push({
              loc: `https://www.ai-tutor.app/${localesNoEN[i].value.toLowerCase()}/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
              priority: 0.5,
              lastmod: new Date().toISOString(),
              alternateRefs: [
                ...localesNoEN.map((locale) => {
                  return {
                    href: `https://www.ai-tutor.app/${locale.value.toLowerCase()}/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
                    hrefIsAbsolute: true,
                    hreflang: locale.value,
                  };
                }),
                {
                  href: `https://www.ai-tutor.app/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
                  hrefIsAbsolute: true,
                  hreflang: "en",
                },
              ],
            });
          }
        }
      }
    }

    // localeページ
    res.push({
      loc: `https://www.ai-tutor.app/`,
      priority: 0.8,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        ...localesNoEN.map((locale) => {
          return {
            href: `https://www.ai-tutor.app/${locale.value.toLowerCase()}/`,
            hrefIsAbsolute: true,
            hreflang: locale.value,
          };
        }),
        {
          href: `https://www.ai-tutor.app/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });

    // mathematicsページ
    for (j in mathematics.data) {
      for (k in mathematics.data[j].units) {
        for (l in mathematics.data[j].units[k].subunits) {
          res.push({
            loc: `https://www.ai-tutor.app/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
            priority: 0.5,
            lastmod: new Date().toISOString(),
            alternateRefs: [
              ...localesNoEN.map((locale) => {
                return {
                  href: `https://www.ai-tutor.app/${locale.value.toLowerCase()}/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
                  hrefIsAbsolute: true,
                  hreflang: locale.value,
                };
              }),
              {
                href: `https://www.ai-tutor.app/mathematics/${mathematics.data[j].path}/${mathematics.data[j].units[k].path}/${mathematics.data[j].units[k].subunits[l].path}/`,
                hrefIsAbsolute: true,
                hreflang: "en",
              },
            ],
          });
        }
      }
    }

    // en
    // homeworkページ
    res.push({
      loc: `https://www.ai-tutor.app/products/homework/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
    });
    // privacy_policyページ
    res.push({
      loc: `https://www.ai-tutor.app/privacy_policy/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/privacy_policy/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/privacy_policy/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });
    // termsページ
    res.push({
      loc: `https://www.ai-tutor.app/terms/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/terms/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/terms/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });
    // tradeページ
    res.push({
      loc: `https://www.ai-tutor.app/trade/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/trade/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/trade/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });

    // ja
    // privacy_policyページ
    res.push({
      loc: `https://www.ai-tutor.app/ja/privacy_policy/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/privacy_policy/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/privacy_policy/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });
    // termsページ
    res.push({
      loc: `https://www.ai-tutor.app/ja/terms/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/terms/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/terms/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });
    // tradeページ
    res.push({
      loc: `https://www.ai-tutor.app/ja/trade/`,
      priority: 0.7,
      lastmod: new Date().toISOString(),
      alternateRefs: [
        {
          href: `https://www.ai-tutor.app/ja/trade/`,
          hrefIsAbsolute: true,
          hreflang: "ja",
        },
        {
          href: `https://www.ai-tutor.app/terms/`,
          hrefIsAbsolute: true,
          hreflang: "en",
        },
      ],
    });
    return res;
  },
};
