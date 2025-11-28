'use client'

import { useTranslation } from 'react-i18next'

export default function Section3() {
  const { t } = useTranslation()

  return (
    <section className="section3">
      <div>
        <h3 dangerouslySetInnerHTML={{ __html: t('section3b.subtitle') }} />
      </div>
      <div>
        <img
          src="/img/2.png"
          alt={t('hero.altText')}
          className="section3-image"
        />
      </div>
    </section>
  )
}