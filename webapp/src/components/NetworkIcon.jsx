// آیکون‌های اختصاصی شبکه — SVG داخلی (بدون نیاز به میزبانی خارجی)، به سبک
// نشان‌های گرد رنگی که اپ‌های صرافی معمولاً برای TRC20/ERC20/BEP20 استفاده
// می‌کنند. رنگ هر کدام با هویت بصری شناخته‌شدهٔ همان شبکه هماهنگ است.

function TronMark() {
  return (
    <svg viewBox="0 0 24 24" width="100%" height="100%">
      <circle cx="12" cy="12" r="12" fill="#EF0027" />
      <path
        d="M6.2 7.4 17.9 9.5l-6.4 9.9-6.7-10.6Zm.9 1.1 4.1 8.9 4.9-7.6-9-1.3Zm5.9-1.9 3.8.7-4.7 4.9.9-5.6Z"
        fill="#fff"
      />
    </svg>
  );
}

function EthMark() {
  return (
    <svg viewBox="0 0 24 24" width="100%" height="100%">
      <circle cx="12" cy="12" r="12" fill="#627EEA" />
      <path d="M12.3 3v6.6l5.6 2.5-5.6-9.1Z" fill="#fff" opacity="0.7" />
      <path d="M12.3 3 6.7 12.1l5.6-2.5V3Z" fill="#fff" />
      <path d="M12.3 16.5v4.5l5.6-7.8-5.6 3.3Z" fill="#fff" opacity="0.7" />
      <path d="M12.3 21v-4.5l-5.6-3.3L12.3 21Z" fill="#fff" />
      <path d="M12.3 15.4 17.9 12l-5.6-2.5v5.9Z" fill="#fff" opacity="0.45" />
      <path d="M6.7 12l5.6 3.4V9.5L6.7 12Z" fill="#fff" opacity="0.8" />
    </svg>
  );
}

function BnbMark() {
  return (
    <svg viewBox="0 0 24 24" width="100%" height="100%">
      <circle cx="12" cy="12" r="12" fill="#F3BA2F" />
      <g fill="#fff">
        <path d="M9 7 12 4l3 3-1.7 1.7L12 7.4l-1.3 1.3L9 7Z" />
        <path d="M4 12l3-3 1.7 1.7L7.4 12l1.3 1.3L7 15l-3-3Z" />
        <path d="M20 12l-3 3-1.7-1.7 1.3-1.3-1.3-1.3L17 9l3 3Z" />
        <path d="M9 17l3 3 3-3-1.7-1.7-1.3 1.3-1.3-1.3L9 17Z" />
        <path d="M12 10.3 13.7 12 12 13.7 10.3 12 12 10.3Z" />
      </g>
    </svg>
  );
}

function GenericMark() {
  return (
    <svg viewBox="0 0 24 24" width="100%" height="100%">
      <circle cx="12" cy="12" r="12" fill="#8E8E93" />
      <circle cx="12" cy="12" r="5" fill="none" stroke="#fff" strokeWidth="1.6" />
    </svg>
  );
}

const MARKS = {
  TRC20: TronMark,
  ERC20: EthMark,
  BEP20: BnbMark,
};

export default function NetworkIcon({ network, size = 20 }) {
  const Mark = MARKS[(network || "").toUpperCase()] || GenericMark;
  return (
    <span style={{ width: size, height: size, display: "inline-flex", flexShrink: 0, borderRadius: "50%", overflow: "hidden" }}>
      <Mark />
    </span>
  );
}
