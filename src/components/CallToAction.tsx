import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function CallToAction() {
  const { t } = useTranslation()
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const checkScreen = () => {
      setIsDesktop(window.innerWidth >= 768)
    }
    checkScreen()
    window.addEventListener('resize', checkScreen)
    return () => window.removeEventListener('resize', checkScreen)
  }, [])

  return (
    <section style={{
      padding: isDesktop ? '80px 0' : '12px 0 0',
      textAlign: 'center'
    }}>
      <div style={isDesktop
        ? {
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'nowrap',
          }
        : {
            padding: '64px 20px',
          }
      }><h2 
        style={{
          fontSize: isDesktop ? '48px' : '32px',
          color: 'black',
          margin: 0,
          textAlign: isDesktop ? 'center' : 'left',
          padding: isDesktop ? '0 0 0 clamp(20px, 8vw, 40px)' : '0',
        }}
        dangerouslySetInnerHTML={{ __html: t('callToAction.title') }}
      />
      <div style={{
      textAlign: 'center',
      width: '50%',
      display: 'flex',
      alignContent: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      margin: isDesktop ? '0' : 'auto',
    }}>
      <img 
        src="/img/aim_logo_Vertical_black.png" 
        alt={t('callToAction.logoAlt')} 
        style={{
          marginTop: isDesktop ? '0' : '24px',
          height: 'auto',
          width: isDesktop ? '40%' : '100%'
        }}
      />
      <div style={{
        marginTop: isDesktop ? '40px' : '24px',
        fontSize: isDesktop ? '1rem' : '0.8rem',
        color: '#1C4EA9',
        fontWeight: '700'
      }}>
        {t('callToAction.trialAvailable')}
      </div>
      <a 
        href="https://apps.apple.com/jp/app/simy/id6745385262" 
        target="_blank" 
        rel="noopener"
        style={{
          margin: isDesktop ? '16px auto' : '32px auto',
          width: isDesktop ? '40%' : '100%',
          height: isDesktop ? '56px' : '44px',
          background: 'linear-gradient(90deg, #2ec6ff 0%, #6fffc2 100%)',
          color: '#fff',
          fontSize: isDesktop ? '1.3rem' : '1rem',
          fontWeight: '600',
          border: 'none',
          borderRadius: isDesktop ? '28px' : '22px',
          boxShadow: '0 2px 8px rgba(46,198,255,0.12)',
          textAlign: 'center',
          lineHeight: isDesktop ? '56px' : '44px',
          textDecoration: 'none',
          cursor: 'pointer',
          transition: 'background 0.2s'
        }}
      >
        {t('callToAction.getStarted')}
      </a>
      </div>
      </div>
    </section>
  )
}