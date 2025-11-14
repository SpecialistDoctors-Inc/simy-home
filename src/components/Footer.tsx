import { useTranslation } from 'react-i18next'

export default function Footer() {
  const { t } = useTranslation()

  return (
    <footer className="footer">
      <div className="footer-inner">
        <a href="/" className="logo-link">
          <img
            src="/img/icon_large.png"
            alt="SIMY"
            className="logo"
          />
        </a>
        <div className="footer-menu">
          <a href="/terms">{t('footer.termsOfUse')}</a>
          <a href="/privacy">{t('footer.privacyPolicy')}</a>
          {/* <a href="/seller-info">{t('footer.sellerInfo')}</a> */}
        </div>
        <div className="awakapp">
          <img 
            src="/img/awakapp_black.png" 
            alt={t('footer.awakappAlt')}
          />
        </div>
        <p className="copyright">{t('footer.copyright')}</p>
      </div>
    </footer>
  )
}