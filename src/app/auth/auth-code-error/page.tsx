export default function AuthCodeErrorPage() {
  return (
    <main style={{ maxWidth: 720, margin: '80px auto', padding: 24 }}>
      <h1>ログインに失敗しました</h1>
      <p>
        OAuth のリダイレクト処理で問題が発生しました。時間をおいて再度お試しいただくか、開発者にお問い合わせください。
      </p>
      <h2>開発者向けヒント</h2>
      <ul>
        <li>
          Supabase の Google プロバイダ設定で、Google Cloud Console に登録した OAuth クライアントの
          Authorized redirect URI に「https://&lt;PROJECT-REF&gt;.supabase.co/auth/v1/callback」が含まれているか確認してください。
        </li>
        <li>
          Next.js 側の開始 URL は「/auth/callback」に設定しています（signInWithOAuth の redirectTo）。
        </li>
        <li>
          Supabase の Auth → URL Configuration で Site URL と Additional Redirect URLs にアプリのドメインや
          「/auth/callback」を必要に応じて追加してください。
        </li>
      </ul>
      <a href="/" style={{ display: 'inline-block', marginTop: 16 }}>トップへ戻る</a>
    </main>
  )
}
