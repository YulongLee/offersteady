import { Fragment, jsxDEV as reactJsxDEV } from "@offersteady/react-jsx-dev-runtime-original";
import { localizeGlobalJsxProps } from "./global-copy";

export { Fragment };
export const jsxDEV = (type: Parameters<typeof reactJsxDEV>[0], props: Record<string, unknown> | null, key: Parameters<typeof reactJsxDEV>[2], isStaticChildren: Parameters<typeof reactJsxDEV>[3], source: Parameters<typeof reactJsxDEV>[4], self: Parameters<typeof reactJsxDEV>[5]) =>
  reactJsxDEV(type, localizeGlobalJsxProps(props), key, isStaticChildren, source, self);
