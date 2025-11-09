"use client";

import { createClient } from '@/utils/supabase/client';
import React from 'react';

type Props = {
  className?: string;
};

/**
 * Google ログインボタン（クライアントコンポーネント）
 */
export default function GoogleLoginButton({  className }: Props) {
  const handleClick = async () => {
      const supabase = createClient()
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });
  };

  return (
    <button
      onClick={handleClick}
      className={className}
      style={{
        background: '#fff',
        color: '#444',
        border: '1px solid #ddd',
        padding: '12px 24px',
        borderRadius: 6,
        margin: '12px 0',
        display: 'flex',
        alignItems: 'center',
        fontSize: 16,
        cursor: 'pointer',
        width: 260,
        justifyContent: 'center',
      }}
    >
      <img
        src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
        alt="Google"
        style={{ width: 24, height: 24, marginRight: 12 }}
      />
      Googleで続行
    </button>
  );
}
