import { globalCompanionCopyByHash, globalCompanionCopyFragments } from "./global-copy.generated";

const HAN = /[\u3400-\u9fff]/;
const hashText = (value: string) => {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
};
const decodeBase64Utf8 = (value: string) => new TextDecoder().decode(
  Uint8Array.from(globalThis.atob(value), character => character.charCodeAt(0)),
);
const fragmentRules = Object.entries(globalCompanionCopyFragments)
  .map(([source, target]) => [decodeBase64Utf8(source), target] as const)
  .sort(([left], [right]) => right.length - left.length);
const translate = (value: string) => {
  if (!HAN.test(value)) return value;
  const leading = value.match(/^\s*/)?.[0] ?? "";
  const trailing = value.match(/\s*$/)?.[0] ?? "";
  const copy = globalCompanionCopyByHash[hashText(value.trim().replace(/\s+/g, " "))];
  if (copy) return `${leading}${copy}${trailing}`;
  let translated = value;
  for (const [source, target] of fragmentRules) translated = translated.split(source).join(target);
  return HAN.test(translated)
    ? "The companion reported an issue. Check device permissions and the connection, then try again."
    : translated;
};
const translateChildren = (children: unknown): unknown => typeof children === "string"
  ? translate(children)
  : Array.isArray(children) ? children.map(translateChildren) : children;
export const localizeGlobalCompanionProps = (props: Record<string, unknown> | null | undefined) => {
  if (!props) return props;
  const next = { ...props };
  if ("children" in next) next.children = translateChildren(next.children);
  for (const key of ["alt", "aria-label", "placeholder", "title"]) {
    if (typeof next[key] === "string") next[key] = translate(next[key] as string);
  }
  return next;
};
