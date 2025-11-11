import { useTranslation } from 'react-i18next'

export default function Hero() {
    const { t } = useTranslation()
  
  return (
    <section className="hero">
      <img 
        src="/img/top.png" 
        alt={t('hero.altText')}
        className="hero-image"
      />
      <h1>人にお願いした仕事<br />今どうなってる？</h1>
      <h2>お願いしたすべてのタスクを、<br />
        ひとつの画面で進捗管理。
        <br /><br />
        止まっているタスクも、<br />
        次に動かすべきアクションも、<br />
        一目で見えるダッシュボード。</h2>
      <a
        href="/login"
        className="header-btn"
      >
          {t('header.getStarted')}
        </a>
    </section>
  )
}