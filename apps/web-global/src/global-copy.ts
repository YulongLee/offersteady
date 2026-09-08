import { globalCopyByHash } from "./global-copy.generated";

const HAN = /[\u3400-\u9fff]/;

export const globalCopyHash = (value: string) => {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
};

export const translateGlobalCopy = (value: string): string => {
  if (!HAN.test(value)) return value;
  if (value === "微信支付、支付宝") return "WeChat Pay and Alipay";
  if (/^\d+天(?:\s*\/\s*\d+天)+$/.test(value)) return value.replace(/天/g, " days");
  if (/^工作日\s+\d{1,2}:\d{2}[–-]\d{1,2}:\d{2}$/.test(value)) return value.replace("工作日", "Weekdays");
  const leading = value.match(/^\s*/)?.[0] ?? "";
  const trailing = value.match(/\s*$/)?.[0] ?? "";
  const normalized = value.trim().replace(/\s+/g, " ");
  const translated = globalCopyByHash[globalCopyHash(normalized)];
  return translated ? `${leading}${translated}${trailing}` : value;
};

const translatedAttributeNames = new Set([
  "alt", "aria-label", "aria-description", "placeholder", "title",
]);

const translateChildren = (children: unknown): unknown => {
  if (typeof children === "string") return translateGlobalCopy(children);
  if (Array.isArray(children)) return children.map(translateChildren);
  return children;
};

export const localizeGlobalJsxProps = (props: Record<string, unknown> | null | undefined) => {
  if (!props) return props;
  let changed = false;
  const next = { ...props };
  if ("children" in next) {
    const translated = translateChildren(next.children);
    if (translated !== next.children) {
      next.children = translated;
      changed = true;
    }
  }
  for (const name of translatedAttributeNames) {
    if (typeof next[name] !== "string") continue;
    const translated = translateGlobalCopy(next[name] as string);
    if (translated !== next[name]) {
      next[name] = translated;
      changed = true;
    }
  }
  return changed ? next : props;
};
