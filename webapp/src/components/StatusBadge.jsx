import { Clock, CheckCircle, Package, XCircle } from "@phosphor-icons/react";

const CONFIG = {
  pending: { label: "در انتظار بررسی", cls: "status-pending", Icon: Clock },
  confirmed: { label: "تایید شده", cls: "status-confirmed", Icon: CheckCircle },
  completed: { label: "تکمیل شده", cls: "status-completed", Icon: Package },
  cancelled: { label: "رد شده", cls: "status-cancelled", Icon: XCircle },
};

export default function StatusBadge({ status, size = 13 }) {
  const cfg = CONFIG[status] || CONFIG.pending;
  const { Icon } = cfg;
  return (
    <span className={`status-badge ${cfg.cls}`}>
      <Icon size={size} weight="fill" />
      {cfg.label}
    </span>
  );
}
