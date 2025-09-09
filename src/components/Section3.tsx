'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Section3() {
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
      position: 'relative', 
      display: 'block', 
      width: '100%',
      backgroundColor: 'black',
      padding: isDesktop ? 'clamp(40px, 12vw, 80px) 0' : 'clamp(20px, 8vw, 30px) 0',
    }}>
      <div style={{
        textAlign: 'center',
        color: 'white',
        width: '100%',
      }}>
        <h2 style={{
          fontSize: isDesktop ? 'clamp(2.8rem, 10vw, 4rem)' : 'clamp(2rem, 8vw, 2rem)',
          fontWeight: 'bold',
          letterSpacing: '0.1em',
          lineHeight: '1.1',
          whiteSpace: isDesktop ? 'pre-line' : 'nowrap',
          overflow: 'hidden'
        }}>
          {t('sections.section3.title')}
        </h2>
      </div>
    </section>
  )
}