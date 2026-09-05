// آدرس‌های برند در یک نقطه نگه‌داری می‌شوند.
export const SARAF_LOGO_URL = "https://i.postimg.cc/B6ZCWdXp/logosaraf.webp";
export const TETHER_LOGO_URL = "https://i.postimg.cc/250WhXsF/tether.png";
export const USDC_LOGO_URL = "https://i.postimg.cc/0QndtT7N/usd-coin-usdc-logo.jpg";

export const ASSET_LOGOS = {
  USDT: TETHER_LOGO_URL,
  USDC: USDC_LOGO_URL,
};

export const ASSET_NAMES_FA = {
  USDT: "تتر",
  USDC: "یو‌اس‌دی کوین",
};

export function normalizeAsset(asset) {
  const value = String(asset || "USDT").toUpperCase();
  return value === "USDC" ? "USDC" : "USDT";
}

export function assetLogo(asset) {
  return ASSET_LOGOS[normalizeAsset(asset)];
}
