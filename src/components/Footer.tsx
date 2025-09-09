import { useTranslation } from 'react-i18next'

export default function Footer() {
  const { t } = useTranslation()

  return (
    <footer className="footer">
      <div className="footer-inner">
        <img 
          src="/img/aim_logo_Horizontal_black_ns.png" 
          alt={t('footer.logoAlt')} 
          className="footer-logo"
        />
        <div className="footer-menu">
          <a href="/terms">{t('footer.termsOfUse')}</a>
          <a href="/privacy">{t('footer.privacyPolicy')}</a>
        </div>
        <div className="awakapp">
          <img 
            src="/img/awakapp.png" 
            alt={t('footer.awakappAlt')}
          />
        </div>
        <p className="copyright">{t('footer.copyright')}</p>
      </div>
    </footer>
  )
}