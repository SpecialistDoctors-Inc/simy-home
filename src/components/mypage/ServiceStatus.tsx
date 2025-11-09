"use client";

type ServiceStatusProps = {
  isActive: boolean;
  isUpdating: boolean;
  onToggle: (newIsActive: boolean) => void;
};

/**
 * サービス利用状態を表示・切り替えるコンポーネント
 */
export default function ServiceStatus({
  isActive,
  isUpdating,
  onToggle,
}: ServiceStatusProps) {
  return (
    <div className="service-status-card">
      <div className="status-content">
        <div>
          <h3 className="status-title">サービス利用状態</h3>
          <p className="status-description">
            {isActive
              ? "サービスは現在利用中です"
              : "サービスは現在停止中です"}
          </p>
        </div>
        <label className={`toggle-switch ${isUpdating ? "disabled" : ""}`}>
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => onToggle(e.target.checked)}
            disabled={isUpdating}
          />
          <span
            className={`toggle-slider ${isActive ? "active" : ""} ${
              isUpdating ? "disabled" : ""
            }`}
          />
        </label>
      </div>
    </div>
  );
}
