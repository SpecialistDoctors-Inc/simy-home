'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';
import Header from '@/components/Header';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';
import AppleLoginButton from '@/components/auth/AppleLoginButton';

export default function AppLoginPage() {
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
      // フラグを設定
      sessionStorage.setItem('app_login', 'true');

      // 既にログイン済みかチェック
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        // 既にログイン済みの場合は、直接mobile-verifyに遷移
        window.location.href = '/auth/mobile-verify';
      } else {
        // 未ログインの場合は、OAuth認証を表示
        setIsChecking(false);
      }
    };

    checkSession();
  }, []);

  // セッションチェック中は読み込み画面を表示
  if (isChecking) {
    return (
      <main>
        <Header />
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        }}>
          <div style={{
            color: 'white',
            fontSize: '20px',
            textAlign: 'center'
          }}>
            <div style={{
              marginBottom: '20px',
              fontSize: '48px'
            }}>
              🔐
            </div>
            <div>セッション確認中...</div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main>
      <Header showInstallButton={false} />
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '100px 20px'
      }}>
        <div style={{
          maxWidth: '500px',
          width: '100%',
          background: 'white',
          borderRadius: '24px',
          padding: '48px 32px',
          textAlign: 'center',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
        }}>
          <h1 style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#1a1a1a',
            marginBottom: '12px'
          }}>
            SIMY アプリログイン
          </h1>

          <p style={{
            fontSize: '16px',
            color: '#666',
            marginBottom: '40px'
          }}>
            GoogleまたはAppleアカウントで<br />
            ログインしてください
          </p>

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px'
          }}>
            <GoogleLoginButton />
            <AppleLoginButton />
          </div>

          <p style={{
            fontSize: '12px',
            color: '#999',
            marginTop: '32px',
            lineHeight: '1.6'
          }}>
            認証後、自動的にアプリが起動します
          </p>
        </div>
      </div>
    </main>
  );
}
