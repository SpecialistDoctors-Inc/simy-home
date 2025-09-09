'use client'

import { useTranslation } from 'react-i18next'

export default function Section2() {
  const { t } = useTranslation()

  return (
    <section style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
      <img 
        src="/img/2.png" 
        alt={t('hero.altText')}
        style={{ width: '100%', height: 'auto',padding:'220px 40px 80px' }}
      />
      <div style={{
        position: 'absolute',
        top: '10%',
        textAlign: 'left',
        color: 'black',
        padding: 'clamp(10px, 3vw, 20px)',
      }}>
        <h2 style={{
          fontSize: 'clamp(1.8rem, 4vw, 3rem)',
          fontWeight: 'bold',
          marginBottom: 'clamp(4px, 1vw, 8px)',
          lineHeight: '1.2',
          whiteSpace: 'pre-line'
        }}>
          {t('sections.section2.title')}
        </h2>
      </div>
    </section>
  )
}