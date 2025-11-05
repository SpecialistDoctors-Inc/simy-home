"use client";

interface UsageDisplayProps {
    currentUsage: number;
    limit: number;
    effectiveDate: string;
}

export default function UsageDisplay({ currentUsage, limit, effectiveDate }: UsageDisplayProps) {
    const usagePercentage = Math.min((currentUsage / limit) * 100, 100);
    const remaining = Math.max(limit - currentUsage, 0);

    return (
        <div className="usage-display-card">
            <div className="effective-date">
                <span className="label">適用日</span>
                <span className="date">{effectiveDate}</span>
            </div>

            <div className="usage-stats">
                <div className="usage-row">
                    <span className="usage-label">現在の利用額</span>
                    <span className="usage-percentage">{usagePercentage.toFixed(0)}%</span>
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
                <span className="remaining-value">${remaining}</span>
            </div>
        </div>
    );
}
