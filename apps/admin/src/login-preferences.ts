const rememberedPhoneKey = "offersteady.admin.remembered-phone";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export function normalizeAdminPhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 13 && digits.startsWith("86")) return digits.slice(2);
  return digits;
}

export function isValidAdminPhone(value: string): boolean {
  return /^1\d{10}$/.test(normalizeAdminPhone(value));
}

export function readRememberedAdminPhone(storage: StorageLike = localStorage): string {
  try {
    const value = normalizeAdminPhone(storage.getItem(rememberedPhoneKey) ?? "");
    return isValidAdminPhone(value) ? value : "";
  } catch {
    return "";
  }
}

export function saveRememberedAdminPhone(phone: string, storage: StorageLike = localStorage): void {
  const normalized = normalizeAdminPhone(phone);
  if (!isValidAdminPhone(normalized)) return;
  try {
    storage.setItem(rememberedPhoneKey, normalized);
  } catch {
    // Login must remain available when browser storage is disabled.
  }
}

export function clearRememberedAdminPhone(storage: StorageLike = localStorage): void {
  try {
    storage.removeItem(rememberedPhoneKey);
  } catch {
    // Login must remain available when browser storage is disabled.
  }
}
