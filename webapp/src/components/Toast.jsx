export default function Toast({ message, onClose }) {
  if (!message) return null;
  setTimeout(() => onClose?.(), 3500);
  return <div className="toast">{message}</div>;
}
