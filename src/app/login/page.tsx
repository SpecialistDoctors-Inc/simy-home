"use client";

import React, { useEffect, useState } from 'react';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';
import AppleLoginButton from '@/components/auth/AppleLoginButton';
import MyPageContent from '@/components/mypage/MyPageContent';
import { createClient } from '@/utils/supabase/client';
import { User } from '@supabase/supabase-js';
import { useTranslation } from 'react-i18next';
import '../../lib/i18n'
import '@/components/mypage/mypage.css';
import Header from '@/components/Header';

/**
 * ログイン/設定統合ページ
 */
export default function Login() {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
      const { i18n } = useTranslation()

    useEffect(() => {
        i18n.changeLanguage('ja')
        const supabase = createClient();

        // 現在のユーザーセッションを取得
        const getUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            setUser(user);
            setLoading(false);
        };

        getUser();

        // 認証状態の変更を監視
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => {
            subscription.unsubscribe();
        };
    }, [i18n]);

    const handleLogout = async () => {
        setUser(null);
    };

    if (loading) {
        return (
            <main>
                <Header fixed={false} showButton={false} />
                <div className="login-loading-container">
                    <div>読み込み中...</div>
                </div>
            </main>
        );
    }

    // ログイン済みの場合はMyPageコンテンツを表示
    if (user) {
        return (
            <main>
                <Header fixed={false} showButton={false} />
                <MyPageContent user={user} onLogout={handleLogout} />
            </main>
        );
    }

    // 未ログインの場合はログインボタンを表示
    return (
        <main>
            <div className="login-welcome-container">
                <a href="/" className="login-page-logo-link">
                    <img
                        src="/img/icon_large.png"
                        alt="SIMY"
                        className="logo login-page-logo"
                    />
                </a>
                <h2 className="login-welcome-heading">ようこそ SIMY へ</h2>
                <GoogleLoginButton />
                <AppleLoginButton />
            </div>
        </main>
    );
}
