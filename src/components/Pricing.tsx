import { useTranslation } from 'react-i18next'

export default function Pricing() {
  const { t } = useTranslation()
 
  return (
    <section className="pricing">
      <h2 className="pricing-title">{t('pricing2.title')}</h2>
      <div className="pricing-container">
        <div className="pricing-card pricing-card-single">
          <div className="pricing-card-header">
            <h3 className="pricing-card-price-large">
              {t('pricing2.price')}
            </h3>
            <p className="pricing-card-tagline">
              {t('pricing2.tagline')}
            </p>
          </div>

          <ul className="pricing-card-features">
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.autoAnalysis')}
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.progressVisualization')}
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.actionSuggestion')}
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.autoLink')}
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.dashboard')}
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              {t('pricing2.features.autoCharge')}
            </li>
          </ul>
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