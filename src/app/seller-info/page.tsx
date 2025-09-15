import Link from 'next/link';
import './seller-info.css';

export default function SellerInfoPage() {
  return (
    <div className="seller-info-container">
      <header className="seller-info-header">
        <h1>特定商取引法に基づく表記</h1>
        <nav>
          <Link href="/">ホームに戻る</Link>
        </nav>
      </header>
      <main className="seller-info-content">
        <section>
          <h2>販売業者</h2>
          <p>AwakApp Inc.</p>
        </section>
        <section>
          <h2>事業所所在地</h2>
          <p>1440 Broadway, Ste 200-1024<br />Oakland, CA 94612, USA</p>
        </section>
        <section>
          <h2>代表者</h2>
          <p>塩飽 哲雄（Tetsuo Shiwaku）</p>
        </section>
        <section>
          <h2>連絡先 / ホームページ</h2>
          <p>
            ウェブサイト: <a href="https://www.awak.app" target="_blank" rel="noopener noreferrer">https://www.awak.app</a><br />
            メール: <a href="mailto:info@awak.app">info@awak.app</a>
          </p>
        </section>
        <section>
          <h2>販売価格</h2>
          <p>価格（該当する税金を含む）は各サービスページに個別に表示されています。詳細については関連するサービスページをご参照ください。</p>
        </section>
        <section>
          <h2>商品引渡し方法・時期</h2>
          <p>すべての製品とサービスはデジタルで提供され、サービスページに別途記載がない限り、支払い後すぐにアクセス可能になります。</p>
        </section>
        <section>
          <h2>支払い方法・時期</h2>
          <p>支払い方法（クレジットカード、Apple Pay、Google Payなど）と支払い時期は各サービスページに記載されています。サービスは支払いが成功した場合にのみ提供されます。</p>
        </section>
        <section>
          <h2>追加費用（送料、税金など）</h2>
          <p>表示価格以外に追加料金はありません。該当する税金はすべて表示価格に含まれています。</p>
        </section>
        <section>
          <h2>返品・キャンセル・撤回に関するポリシー</h2>
          <p>デジタルサービスの性質上、すべての購入は最終的なものであり、返金はできません。キャンセルは各サービスに指定された手順に従って行うことができますが、既に支払われた金額に対する返金は行われません。</p>
        </section>
        <section>
          <h2>不良品またはサービスの中断</h2>
          <p>すべてのデジタルサービスは「現状有姿」で提供されます。当社の過失により技術的な問題でサービスを適切に使用できない場合は、7日以内にご連絡ください。問題を確認し、適切なサポートを提供いたします。</p>
        </section>
      </main>
      <footer>
        <div className="footer-links">
          <Link href="/">ホーム</Link>
          <span className="separator">|</span>
          <Link href="/privacy">プライバシーポリシー</Link>
          <span className="separator">|</span>
          <Link href="/terms">利用規約</Link>
        </div>
        <p className="copyright">&copy; 2025 AI Mentor. All rights reserved.</p>
      </footer>
    </div>
  );
}
