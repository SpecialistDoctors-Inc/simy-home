'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Section4() {
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
            padding: 'clamp(40px, 6vw, 80px) 0 0',
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            paddingTop: '120px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'nowrap',
          }
        : {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            padding: '80px 0 0',
          }
      }>
        <h2 style={isDesktop
          ? {
              padding: 'clamp(20px, 6vw, 40px)',
              fontSize: '4rem',
              fontWeight: 'bold',
              lineHeight: '1.1',
              whiteSpace: 'pre-line'
            }
          : {
              padding: '24px 24px 0',
              fontSize: 'clamp(2.2rem, 6vw, 3rem)',
              fontWeight: 'bold',
              lineHeight: '1.1',
              margin: 0,
              whiteSpace: 'pre-line'
            }
        }>
          {t('sections.section4.title')}
        </h2>
        <img 
          src="/img/4.png" 
          alt={t('hero.altText')}
          style={isDesktop
            ? { width: '40%', height: 'auto', display: 'block',marginRight:'0' }
            : { width: '100%', height: 'auto' ,marginTop:'40px'}
          }
        />
      </div>
      <div style={isDesktop
        ? {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            padding: 'clamp(20px, 6vw, 40px)',
            paddingBottom: '40px'
          }
        : {
            textAlign: 'left',
            color: '#000000',
            textShadow: 'none',
            padding: 'clamp(20px, 4vw, 40px)',
            paddingBottom: '40px'
          }
      }>
        <h3 style={isDesktop
          ? {
              fontSize: 'clamp(2rem, 5vw, 3rem)',
              fontWeight: 'bold',
              lineHeight: '1.2',
              margin: '16px 0 20px 0',
              whiteSpace: 'pre-line'
            }
          : {
              fontSize: 'clamp(1.6rem, 4vw, 2.4rem)',
              fontWeight: 'bold',
              lineHeight: '1.2',
              margin: '8px 0 10px 0',
              whiteSpace: 'pre-line'
            }
        }>
          {t('sections.section4.subtitle')}
        </h3>
        <p style={isDesktop
          ? {
              fontSize: 'clamp(1.2rem, 4vw, 1.6rem)',
              lineHeight: '1.6',
              whiteSpace: 'pre-line',
              margin: '16px 0 0 0'
            }
          : {
              fontSize: '0.8rem',
              whiteSpace: 'pre-line',
              lineHeight: '1.4',
              margin: '10px 10px 10px 10px'
            }
        }>
          {t('sections.section4.description')}
        </p>
      </div>
    </section>
  )
}