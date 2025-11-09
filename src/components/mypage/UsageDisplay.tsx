"use client";

interface UsageDisplayProps {
  currentUsage: number;
  limit: number;
  effectiveDate: string;
}

export default function UsageDisplay({
  currentUsage,
  limit,
  effectiveDate,
}: UsageDisplayProps) {
  const usagePercentage =
    limit == 0 ? 0 : Math.min((currentUsage / limit) * 100, 100);
  const remaining = limit == 0 ? 0 : Math.max(limit - currentUsage, 0);

  return (
    <div className="usage-display-card">
      <div className="effective-date">
        <span className="label">リセット日</span>
        <span className="date">{effectiveDate}</span>
      </div>

      <div className="usage-stats">
        <div className="usage-row">
          <span className="usage-label">現在の利用額</span>
          <span className="usage-percentage">
            {limit === 0 ? "" : `${usagePercentage.toFixed(0)}%`}
          </span>
          <span className="usage-amount">${currentUsage}</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${usagePercentage}%` }}
          />
        </div>
      </div>

      <div className="remaining-amount">
        <span className="remaining-label">残り</span>
        <span className="remaining-value">
          {limit === 0 ? "上限未設定" : `$${remaining}`}
        </span>
      </div>
    </div>
  );
}
