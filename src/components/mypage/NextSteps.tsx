"use client";

import { createClient } from "@/utils/supabase/client";

interface NextStepsProps {
  hasPaymentMethod: boolean;
  userId: string;
}

export default function NextSteps({ 
  hasPaymentMethod,
  userId
 }: NextStepsProps) {
  const handleRegisterCard = async () => {
    try {
        const supabase = createClient();

        // アプリからのアクセスかチェック
        const isFromApp = sessionStorage.getItem('app_login') === 'true';

        const { data, error } = await supabase.functions.invoke('stripe-start-session', {
            body: {
              user_id: userId,
              success_url: isFromApp
                  ? window.location.origin + "/auth/mobile-verify"
                  : (hasPaymentMethod ? window.location.origin + "/login" : window.location.origin + "/redirect"),
              cancel_url: window.location.origin + "/login",
            }
        });

        if (error) {
            throw error;
        }

        const { url } = (data ?? {}) as { url?: string };
        if (!url) throw new Error('Invalid session URL');
        window.location.href = url;

    } catch (error) {
        console.error('Error opening payment setup:', error);
        alert('支払い設定の開始に失敗しました。時間をおいて再度お試しください。');
    }
  };

  return (
    <div className="next-steps">
      <h3 className="next-steps-title">次のステップ</h3>
      
      <div className="step-item">
          <div className="step-number-container">
            <div className="step-number active">1</div>
            <div className="step-divider"></div>
          </div>
          <div className="step-content">
            <p className="step-label">支払い方法を登録</p>
            <button className="step-action-btn btn" onClick={handleRegisterCard}>
            カードを登録する
            </button>
          </div>
      </div>

      <div className="step-item">
          <div className="step-number-container">
            <div className="step-number">2</div>
          </div>
          <div className="step-content">
          <p className="step-label">SIMYを起動してタスクを解析 ✨</p>
          </div>
      </div>
    </div>
  );
}
