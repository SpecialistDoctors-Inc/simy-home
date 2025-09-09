'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Section2() {
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
            color: 'black',
            textAlign: 'left',
            padding: '0 clamp(20px, 6vw, 40px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'nowrap',
          }
        : {
            color: 'black',
            textAlign: 'left',
            padding: 'clamp(10px, 3vw, 20px)',
          }
      }>
        <h2 style={isDesktop
          ? {
              fontSize: 'clamp(1.2rem, 3.4vw, 3rem)',
              fontWeight: 'bold',
              marginBottom: 'clamp(8px, 2vw, 16px)',
              lineHeight: '1.4',
              whiteSpace: 'pre-line'
            }
          : {
              fontSize: 'clamp(1.8rem, 4vw, 3rem)',
              fontWeight: 'bold',
              marginBottom: 'clamp(4px, 1vw, 8px)',
              lineHeight: '1.2',
              whiteSpace: 'pre-line'
            }
        }>
          {t('sections.section2.title')}
        </h2>
         <img 
          src="/img/2.png" 
          alt={t('hero.altText')}
          style={isDesktop
            ? { width: '50%', height: 'auto', padding: '60px 40px 60px' }
            : { width: '100%', height: 'auto', padding: '20px' }
        }
      />
      </div>
    </section>
  )
}