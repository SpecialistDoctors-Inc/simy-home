"use client";

import { useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';

/**
 * OAuth認証のコールバックページ（クライアントサイド）
 * S3静的ホスティング用 - PKCEフロー対応
 */
export default function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const handleCallback = async () => {
      try {
        const supabase = createClient();
        const params = new URLSearchParams(window.location.search);

        // Supabaseが自動的にURLを検出してセッションに変換するまで少し待つ
        await new Promise(resolve => setTimeout(resolve, 1000));

        if (!mounted) return;

        // 現在のセッションを確認
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (!mounted) return;

        if (sessionError) {
          console.error('❌ Session error:', sessionError);
          setError(sessionError.message);
          setTimeout(() => {
            if (mounted) {
              window.location.href = '/login?error=session_failed';
            }
          }, 2000);
          return;
        }

        if (session) {
          window.location.href = '/login';
        } else {
          const code = params.get('code');

          if (code) {
            const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

            if (!mounted) return;

            if (exchangeError) {
              console.error('❌ Exchange error:', exchangeError);
              setError(exchangeError.message);
              setTimeout(() => {
                if (mounted) {
                  window.location.href = '/login?error=exchange_failed';
                }
              }, 2000);
            } else if (data.session) {
              window.location.href = '/login';
            }
          } else {
            console.error('❌ No code and no session');
            setError('認証コードが見つかりません');
            setTimeout(() => {
              if (mounted) {
                window.location.href = '/login?error=no_code';
              }
            }, 2000);
          }
        }
      } catch (err) {
        console.error('❌ Unexpected error:', err);
        if (!mounted) return;
        setError(err instanceof Error ? err.message : String(err));
        setTimeout(() => {
          if (mounted) {
            window.location.href = '/login?error=unexpected';
          }
        }, 2000);
      }
    };

    handleCallback();

    return () => {
      mounted = false;
    };
  }, []);

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
