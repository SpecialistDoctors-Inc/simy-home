"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase/client';

/**
 * OAuth認証のコールバックページ（クライアントサイド）
 * S3静的ホスティング用 - PKCEフロー対応
 */
export default function AuthCallback() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const supabase = createClient();
        const params = new URLSearchParams(window.location.search);

        console.log('=== AUTH CALLBACK DEBUG ===');
        console.log('Full URL:', window.location.href);
        console.log('Search params:', window.location.search);
        console.log('All params:', Object.fromEntries(params.entries()));

        // Supabaseが自動的にURLを検出してセッションに変換するまで少し待つ
        await new Promise(resolve => setTimeout(resolve, 1000));

        // 現在のセッションを確認
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        console.log('Session check result:');
        console.log('Session:', session);
        console.log('Error:', sessionError);

        if (sessionError) {
          console.error('❌ Session error:', sessionError);
          setError(sessionError.message);
          setTimeout(() => router.push('/login?error=session_failed'), 3000);
          return;
        }

        if (session) {
          console.log('✅ Auth success! User:', session.user.email);
          const next = params.get('next') || '/login';
          router.push(next.startsWith('/') ? next : '/login');
        } else {
          console.log('⚠️ No session found, checking for code...');
          const code = params.get('code');

          if (code) {
            console.log('Code found, manually exchanging...');
            const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

            if (exchangeError) {
              console.error('❌ Exchange error:', exchangeError);
              setError(exchangeError.message);
              setTimeout(() => router.push('/login?error=exchange_failed'), 3000);
            } else if (data.session) {
              console.log('✅ Manual exchange success!');
              const next = params.get('next') || '/login';
              router.push(next.startsWith('/') ? next : '/login');
            }
          } else {
            console.error('❌ No code and no session');
            setError('認証コードが見つかりません');
            setTimeout(() => router.push('/login?error=no_code'), 3000);
          }
        }
      } catch (err) {
        console.error('❌ Unexpected error:', err);
        setError(err instanceof Error ? err.message : String(err));
        setTimeout(() => router.push('/login?error=unexpected'), 3000);
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: 20
    }}>
      <div>認証中...</div>
      <div style={{ fontSize: 14, color: '#666' }}>
        しばらくお待ちください
      </div>
      {error && (
        <div style={{
          fontSize: 14,
          color: '#ff4444',
          marginTop: 20,
          padding: '10px 20px',
          background: '#ffeeee',
          borderRadius: 6,
          maxWidth: 400,
          textAlign: 'center'
        }}>
          エラー: {error}
        </div>
      )}
    </div>
  );
}
