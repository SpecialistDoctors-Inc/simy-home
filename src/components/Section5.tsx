'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Section5() {
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
    <section style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
      <div style={isDesktop
        ? {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            padding: 'clamp(40px, 6vw, 80px) 0 0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'nowrap',
          }
        : {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
          }
      }>
        <h2 style={isDesktop
          ? {
              fontSize: 'clamp(3rem, 7vw, 4rem)',
              padding: 'clamp(20px, 6vw, 40px)',
              fontWeight: 'bold',
              lineHeight: '1.1',
              whiteSpace: 'pre-line'
            }
          : {
              padding: '24px 24px 0',
              fontSize: 'clamp(2.6rem, 6vw, 4rem)',
              fontWeight: 'bold',
              lineHeight: '1.1',
              whiteSpace: 'pre-line'
            }
        }>
          {t('sections.section5.title')}
        </h2> 
        <img 
        src="/img/5.png" 
        alt={t('hero.altText')}
        style={isDesktop
          ? { width: '40%', height: 'auto',marginRight:'0', display: 'block' }
          : { width: '100%', height: 'auto' }
        }
      />
      </div>
      <div style={isDesktop
        ? {
            bottom: '0',
            textAlign: 'left',
            color: 'black',
            textShadow: 'none',
            padding: 'clamp(30px, 6vw, 60px)',
          }
        : {
            bottom: '0',
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
              textAlign: 'center'
            }
          : {
              fontSize: 'clamp(1.6rem, 4vw, 2.4rem)',
              fontWeight: 'bold',
              wordSpacing: '0.1em',
              lineHeight: '1.2',
              margin: '4px 0 10px 0',
              whiteSpace: 'pre-line',
              textAlign: 'center'
            }
        }>
          {t('sections.section5.subtitle')}
        </h3>
        <p style={isDesktop
          ? {
              fontSize: 'clamp(1.2rem, 4vw, 1.6rem)',
              whiteSpace: 'pre-line',
              lineHeight: '1.6',
              margin: '20px 0 0 0'
            }
          : {
              fontSize: 'clamp(0.8rem, 3vw, 1.2rem)',
              whiteSpace: 'pre-line',
              lineHeight: '1.4',
              margin: '10px 0 0 0'
            }
        }>
          {t('sections.section5.description')}
        </p>
      </div>
    </section>
  )
}