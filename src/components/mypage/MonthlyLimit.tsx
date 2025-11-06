"use client";

import { useEffect, useState } from "react";

interface MonthlyLimitProps {
  defaultLimit: number;
  onLimitChange?: (newLimit: number) => void;
}

const PRESET_VALUES = [10, 30, 50, 100];

export default function MonthlyLimit({
  defaultLimit,
  onLimitChange,
}: MonthlyLimitProps) {
  const [limit, setLimit] = useState(defaultLimit);
  const [isSafetyLocked, setIsSafetyLocked] = useState(
    defaultLimit == 0 ? false : true
  );

  // 親の defaultLimit が更新されたら内部 state も更新
  useEffect(() => {
    setLimit(defaultLimit);
    setIsSafetyLocked(defaultLimit == 0 ? false : true);
  }, [defaultLimit]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isSafetyLocked) return;
    const newValue = Number(e.target.value);
    setLimit(newValue);
    onLimitChange?.(newValue);
  };

  const handlePresetClick = (value: number) => {
    if (!isSafetyLocked) return;
    setLimit(value);
    onLimitChange?.(value);
  };

  const handleIsSafetyCheck = (checked: boolean) => {
    if (!checked) {
      setLimit(0);
      onLimitChange?.(0);
    } else {
      setLimit(10);
      onLimitChange?.(10);
    }
    setIsSafetyLocked(checked);
  };

  return (
    <div className="monthly-limit-card">
      <h2 className="card-title">月額上限</h2>
      <p className="card-description">今月の利用上限額を設定してください。</p>

      <div className="limit-display">
        <span className="limit-amount">
          {!isSafetyLocked ? "上限未設定" : `${limit}USD`}
        </span>
      </div>

      <div className="slider-container">
        <input
          type="range"
          min="10"
          max="300"
          value={limit}
          onChange={handleSliderChange}
          className={`slider ${!isSafetyLocked ? "locked" : ""}`}
          disabled={!isSafetyLocked}
          style={{
            background: `linear-gradient(to right, ${!isSafetyLocked ? "#999" : "#0066FF"} 0%, ${!isSafetyLocked ? "#999" : "#0066FF"} ${((limit - 10) / (300 - 10)) * 100}%, #e5e5e5 ${((limit - 10) / (300 - 10)) * 100}%, #e5e5e5 100%)`,
          }}
        />
        <div className="slider-labels">
          <span>$10</span>
          <span>$300</span>
        </div>
      </div>

      <div className="preset-buttons">
        {PRESET_VALUES.map((value) => (
          <button
            key={value}
            onClick={() => handlePresetClick(value)}
            className={`preset-btn ${limit === value ? "active" : ""} ${!isSafetyLocked ? "locked" : ""}`}
            disabled={!isSafetyLocked}
          >
            ${value}
          </button>
        ))}
      </div>

      <div className="safety-lock-container">
        <label className="safety-lock-label">
          <input
            type="checkbox"
            checked={isSafetyLocked}
            onChange={(e) => handleIsSafetyCheck(e.target.checked)}
          />
          <span style={{ fontSize: "18px", fontWeight: "600" }}>
            Safetyロック
          </span>
        </label>
      </div>

      <p className="warning-text">
        上限に達すると課金が停止されます。
        <br />
        AI機能は一時的に無効になります。
      </p>
    </div>
  );
}
