import { useTranslation } from 'react-i18next'

export default function Pricing() {
  const { t } = useTranslation()
 
  return (
    <section className="pricing">
      <h2 className="pricing-title">価格表</h2>
      <h3 className="pricing-subtitle">使った分だけ<br/>トークン数に応じた料金体系</h3>
      <div className="pricing-container">
        <div className="pricing-card pricing-card-single">
          <div className="pricing-card-header">
            <h3 className="pricing-card-price-large">
              0-1 USD<span className="pricing-card-period-inline">/月（税別）</span>
            </h3>
            <p className="pricing-card-tagline">
              上限ガード付き・従量課金制
            </p>
          </div>
          
          <ul className="pricing-card-features">
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              Gmail / Slack / Zoom の会話をAIが自動解析
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              他人に依頼した仕事の進捗を自動で整理・可視化
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              停滞している依頼や次に動かすべきアクションを提示
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              関連するタスクを文脈から自動リンク
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              ダッシュボードで「誰が・何を・どこまで」一目で把握
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              利用量に応じて自動課金
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              月1 USDで自動停止(上限ガード)
            </li>
            <li className="pricing-card-feature">
              <span className="pricing-card-feature-check">•</span>
              1 USD単位または任意金額でトップアップ可能
            </li>
          </ul>
          <a
            href="/login"
            className="header-btn"
          >
            {t('header.getStarted')}
          </a>
        </div>
      </div>
    </section>
  )
}