import { useTranslation } from 'react-i18next'

export default function Hero() {
    const { t } = useTranslation()
  
  return (
    <section className="hero">
      <div>
        <img 
          src="/img/fv.png" 
          alt={t('hero.altText')}
          className="hero-image"
        />
      </div>
      <div>
        <h1 dangerouslySetInnerHTML={{ __html: t('hero2.title') }} />
        <h2 dangerouslySetInnerHTML={{ __html: t('hero2.subtitle') }} />
        <div>
          <a
            href="https://apps.apple.com/jp/app/simy/id6745385262"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
          >
            <img
              src="/img/apple_install.svg"
              alt="Download on the App Store"
              className="appstore-badge"
            />
          </a>
        </div>
      </div>
    </section>
  )
}