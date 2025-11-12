'use client'

import { useTranslation } from 'react-i18next'

export default function Section2() {
  const { t } = useTranslation()

  return (
    <section className="section2">
      <h2>SIMYのご紹介</h2>
      <h3>❶ SlackやZoom、Teamsの会話を<br/>
      AIが読み取り、進捗を自動で整理・更新</h3>
      <img 
        src="/img/1.png" 
        alt={t('hero.altText')}
        className="section2-image"
      />
    </section>
  )
}