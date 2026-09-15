import { List } from "@phosphor-icons/react";

export default function AppMenu({ navigate, triggerClassName = "icon-button", triggerIconSize = 24 }) {
  return (
    <button
      className={triggerClassName}
      aria-label="باز کردن منو"
      onClick={() => navigate("menu")}
    >
      <List size={triggerIconSize} />
    </button>
  );
}
