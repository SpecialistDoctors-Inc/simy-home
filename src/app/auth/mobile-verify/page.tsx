'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';

const APP_SCHEME = 'simy.dev:';
const APP_STORE_URL = 'https://apps.apple.com/jp/app/simy/id6745385262';

export default function MobileVerifyPage() {
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');

  useEffect(() => {
    const handleAuth = async () => {
      try {
        const supabase = createClient();

        // URLからトークンを自動検出してセッション確立
        // Supabaseが自動的に処理（detectSessionInUrl: trueのため）
        await new Promise(resolve => setTimeout(resolve, 1500));

        // セッションを取得
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          throw sessionError;
        }

        if (session) {
          setStatus('success');

          // セッショントークンをアプリに渡す
          const deepLink = `simy.dev:/auth-success?access_token=${session.access_token}&refresh_token=${session.refresh_token}`;

          console.log('🚀 アプリ起動:', deepLink);

          // カスタムURLスキームでアプリ起動
          window.location.href = deepLink;

          // フォールバック: アプリが起動しなかった場合
          setTimeout(() => {
            if (document.visibilityState === 'visible') {
              // ページがまだ表示されている = アプリが起動しなかった
              console.log('⚠️ アプリ起動失敗、App Storeへリダイレクト');
              window.location.href = APP_STORE_URL;
            }
          }, 2500);
        } else {
          throw new Error('セッションの確立に失敗しました');
        }
      } catch (err) {
        console.error('❌ Auth error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : '認証に失敗しました');

        // エラー時もApp Storeへ誘導
        setTimeout(() => {
          window.location.href = APP_STORE_URL;
        }, 3000);
      }
    };

    handleAuth();
  }, []);

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: 20,
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      padding: '20px',
      textAlign: 'center'
    }}>
      {status === 'verifying' && (
        <>
          <div style={{
            width: 80,
            height: 80,
            border: '6px solid rgba(255,255,255,0.3)',
            borderTop: '6px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <div style={{ fontSize: 24, fontWeight: 600, marginTop: 10 }}>
            🔐 認証中...
          </div>
          <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.8)' }}>
            しばらくお待ちください
          </div>
        </>
      )}

      {status === 'success' && (
        <>
          <div style={{ fontSize: 80 }}>✅</div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>認証成功！</div>
          <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.9)' }}>
            アプリを起動中...
          </div>
          <div style={{
            marginTop: 20,
            fontSize: 14,
            color: 'rgba(255,255,255,0.7)',
            maxWidth: 300
          }}>
            アプリが起動しない場合は、<br />
            App Storeから再インストールしてください
          </div>
        </>
      )}

      {status === 'error' && (
        <>
          <div style={{ fontSize: 80 }}>❌</div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>認証エラー</div>
          <div style={{
            fontSize: 14,
            background: 'rgba(255,255,255,0.2)',
            padding: '16px 24px',
            borderRadius: 12,
            maxWidth: 400,
            wordBreak: 'break-word'
          }}>
            {error}
          </div>
          <div style={{ fontSize: 14, marginTop: 10, color: 'rgba(255,255,255,0.8)' }}>
            App Storeにリダイレクトします...
          </div>
        </>
      )}

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
