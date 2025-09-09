'use client'

import { useTranslation } from 'react-i18next'

export default function Section4() {
  const { t } = useTranslation()

  return (
    <section style={{ position: 'relative', display: 'inline-block', width: '100%',backgroundColor: '#EDEDED' }}>
      <div style={{
        textAlign: 'left',
        color: '#000000',
        textShadow: 'none',
        padding: 'clamp(20px, 4vw, 40px)',
        paddingTop:'80px'
      }}>
        <h2 style={{
          fontSize: 'clamp(3rem, 6vw, 4rem)',
          fontWeight: 'bold',
          lineHeight: '1.1',
          margin: 0,
          whiteSpace: 'pre-line'
        }}>
          {t('sections.section4.title')}
        </h2>
      </div><img 
        src="/img/4.png" 
        alt={t('hero.altText')}
        style={{ width: '100%', height: 'auto'}}
      />
        <div style={{
        textAlign: 'left',
        color: '#000000',
        textShadow: 'none',
        padding: 'clamp(20px, 4vw, 40px)',
        paddingBottom:'80px'
      }}>
        <h3 style={{
          fontSize: 'clamp(1.6rem, 4vw, 2.4rem)',
          fontWeight: 'bold',
          lineHeight: '1.2',
          margin: '8px 0 10px 0',
          whiteSpace: 'pre-line'
        }}>
          {t('sections.section4.subtitle')}
        </h3>
        <p style={{
          fontSize: 'clamp(0.8rem, 3vw, 1.2rem)',
          lineHeight: '1.4',
          margin: '10px 0 0 0'
        }}>
          {t('sections.section4.description')}
        </p>
      </div>
    </section>
  )
}