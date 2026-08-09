import { WarningCircle } from "@phosphor-icons/react";

export default function Toast({ message, onClose }) {
  if (!message) return null;
  setTimeout(() => onClose?.(), 3500);
  return (
    <div className="toast animate-in">
      <WarningCircle size={18} weight="fill" />
      <span>{message}</span>
    </div>
  );
}
