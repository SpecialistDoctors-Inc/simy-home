import { useTranslation } from 'react-i18next'

export default function CallToAction() {
  const { t } = useTranslation()

  return (
    <section style={{
      padding: '32px 0 64px',
      textAlign: 'center'
    }}>
      <h2 
        style={{
          fontSize: '32px',
          color: 'black',
          margin: 0,
          textAlign: 'left',
          padding: 'clamp(20px, 4vw, 40px)',
        }}
        dangerouslySetInnerHTML={{ __html: t('callToAction.title') }}
      />
      <img 
        src="/img/aim_logo_Vertical_black.png" 
        alt={t('callToAction.logoAlt')} 
        style={{
          marginTop: '24px',
          height: 'auto',
          width: '50%'
        }}
      />
      <div style={{
        marginTop: '24px',
        fontSize: '0.8rem',
        color: '#1C4EA9',
        fontWeight: '700'
      }}>
        {t('callToAction.trialAvailable')}
      </div>
      <a 
        href="https://apps.apple.com/us/app/ai-mentor-app/id6745385262" 
        target="_blank" 
        rel="noopener"
        style={{
          marginTop: '8px',
          display: 'inline-block',
          width: '70%',
          height: '44px',
          background: 'linear-gradient(90deg, #2ec6ff 0%, #6fffc2 100%)',
          color: '#fff',
          fontSize: '1rem',
          fontWeight: '600',
          border: 'none',
          borderRadius: '22px',
          boxShadow: '0 2px 8px rgba(46,198,255,0.12)',
          textAlign: 'center',
          lineHeight: '44px',
          textDecoration: 'none',
          cursor: 'pointer',
          transition: 'background 0.2s'
        }}
      >
        {t('callToAction.getStarted')}
      </a>
    </section>
  )
}