import { Fragment, jsx as reactJsx, jsxs as reactJsxs } from "@offersteady/desktop-react-jsx-runtime-original";
import { localizeGlobalCompanionProps } from "./global-copy";
export { Fragment };
export const jsx = (type: Parameters<typeof reactJsx>[0], props: Record<string, unknown> | null, key?: string) => reactJsx(type, localizeGlobalCompanionProps(props), key);
export const jsxs = (type: Parameters<typeof reactJsxs>[0], props: Record<string, unknown> | null, key?: string) => reactJsxs(type, localizeGlobalCompanionProps(props), key);
