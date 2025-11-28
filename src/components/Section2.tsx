'use client'

import { useTranslation } from 'react-i18next'

export default function Section2() {
  const { t } = useTranslation()

  return (
    <section className="section2">
      <div>
        <h2>{t('section2b.title')}</h2>
        <h3 dangerouslySetInnerHTML={{ __html: t('section2b.subtitle') }} />
      </div>
      <div>
        <img
          src="/img/1.png"
          alt={t('hero.altText')}
          className="section2-image"
        />
      </div>
    </section>
  )
}