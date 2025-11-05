import { Metadata } from 'next';
import React from 'react';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';
import AppleLoginButton from '@/components/auth/AppleLoginButton';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: 'Login - AI Mentor',
  description: 'Login for AI Mentor application',
}

export default function Login() {
    return (
        <main>
            <Header />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 120 }}>
                <h2 style={{marginBottom:40}}>Login / Sign Up</h2>
                <GoogleLoginButton />
                <AppleLoginButton />
            </div>
        </main>
    );
};