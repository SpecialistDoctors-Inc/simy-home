'use client'

import { useTranslation } from 'react-i18next'

export default function Section3() {
  const { t } = useTranslation()

  return (
    <section style={{ 
      position: 'relative', 
      display: 'block', 
      width: '100%',
      backgroundColor: 'black',
      padding: 'clamp(20px, 8vw, 30px)'
    }}>
      <div style={{
        textAlign: 'center',
        color: 'white',
        width: '100%',
      }}>
        <h2 style={{
          fontSize: 'clamp(2rem, 8vw, 3rem)',
          fontWeight: 'bold',
          letterSpacing: '0.1em',
          lineHeight: '1.1',
          whiteSpace: 'pre-line',
          overflow: 'hidden'
        }}>
          {t('sections.section3.title')}
        </h2>
      </div>
    </section>
  )
}