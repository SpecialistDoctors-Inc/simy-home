"use client";

interface NextStepsProps {
  hasPaymentMethod: boolean;
}

export default function NextSteps({ hasPaymentMethod }: NextStepsProps) {
  const handleRegisterCard = () => {
    // カード登録画面へ遷移
    // PaymentMethodコンポーネントの管理ボタンと同じ動作
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
