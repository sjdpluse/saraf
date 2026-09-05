export const IN_PERSON_ADDRESS = "کوته‌سنگی، همادی مارکیت، کابل، افغانستان";
export const IN_PERSON_REPRESENTATIVE_PHONE = "0790810632";
export const SARAF_SUPPORT_PHONE = "0775146747";

export function generateInPersonCode() {
  if (globalThis.crypto?.getRandomValues) {
    const value = new Uint32Array(1);
    globalThis.crypto.getRandomValues(value);
    return String(1000 + (value[0] % 9000));
  }
  return String(Math.floor(1000 + Math.random() * 9000));
}
