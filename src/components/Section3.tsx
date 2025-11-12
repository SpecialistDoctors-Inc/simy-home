'use client'

import { useTranslation } from 'react-i18next'

export default function Section3() {
  const { t } = useTranslation()

  return (
    <section className="section3">
      <h3>❷ 個々人の止まっているタスクも、<br/>
      次に動かすべきアクションも、<br/>
      一目で見えるダッシュボード</h3>
      <img 
        src="/img/2.png" 
        alt={t('hero.altText')}
        className="section3-image"
      />
    </section>
  )
}