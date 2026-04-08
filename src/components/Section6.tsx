'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Section6() {
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
    <section style={{ position: 'relative', display: 'inline-block', width: '100%', backgroundColor: '#EDEDED' }}>
      <div style={isDesktop
        ? {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            paddingTop: '100px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'nowrap',
            padding: 'clamp(40px, 6vw, 80px) 0 0',
          }
        : {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            paddingTop: '50px'
          }
      }>
        <h2 style={isDesktop
          ? {
              padding: 'clamp(20px, 6vw, 40px)',
              fontSize: 'clamp(3.2rem, 7vw, 4rem)',
              fontWeight: 'bold',
              lineHeight: '1.1',
              whiteSpace: 'pre-line'
            }
          : {
              fontSize: '2.2rem',
              padding: '50px 24px 24px',
              fontWeight: 'bold',
              lineHeight: '1.1',
              whiteSpace: 'pre-line'
            }
        }>
          {t('sections.section6.title')}
        </h2>
        <img 
          src="/img/6.png" 
          alt={t('howItWorks.goalMomentumAlt')}
          style={isDesktop
            ? { width: '40%', height: 'auto',marginRight:'0', display: 'block' }
            : { width: '100%', height: 'auto' }
          }
        />
      </div>
      <div style={isDesktop
        ? {
            textAlign: 'left',
            color: 'black',
            textShadow: 'none',
            padding: 'clamp(20px, 6vw, 40px)',
            paddingBottom: '40px'          }
        : {
            textAlign: 'left',
            color: 'black',
            textShadow: 'none',
            padding: 'clamp(20px, 4vw, 40px)',
          }
      }>
        <h3 style={isDesktop
          ? {
              fontSize: 'clamp(2rem, 5vw, 3rem)',
              fontWeight: 'bold',
              wordSpacing: '0.1em',
              lineHeight: '1.2',
              margin: '8px 0 16px 0',
              whiteSpace: 'pre-line',
              textAlign: 'left'
            }
          : {
              fontSize: 'clamp(1.6rem, 4vw, 2.4rem)',
              fontWeight: 'bold',
              wordSpacing: '0.1em',
              lineHeight: '1.2',
              margin: '4px 0 10px 0',
              whiteSpace: 'pre-line',
              textAlign: 'left'
            }
        }>
          {t('sections.section6.subtitle')}
        </h3>
        <p style={isDesktop
          ? {
              fontSize: 'clamp(1.2rem, 4vw, 1.6rem)',
              whiteSpace: 'pre-line',
              lineHeight: '1.6',
              margin: '16px 0 0 0'
            }
          : {
              fontSize: '0.8rem',
              whiteSpace: 'pre-line',
              lineHeight: '1.4',
              margin: '10px 10px 10px 10px'
            }
        }>
          {t('sections.section6.description')}
        </p>
      </div>
    </section>
  )
}