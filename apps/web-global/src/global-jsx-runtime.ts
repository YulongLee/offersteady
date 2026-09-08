import { Fragment, jsx as reactJsx, jsxs as reactJsxs } from "@offersteady/react-jsx-runtime-original";
import { localizeGlobalJsxProps } from "./global-copy";

export { Fragment };
export const jsx = (type: Parameters<typeof reactJsx>[0], props: Record<string, unknown> | null, key?: string) => reactJsx(type, localizeGlobalJsxProps(props), key);
export const jsxs = (type: Parameters<typeof reactJsxs>[0], props: Record<string, unknown> | null, key?: string) => reactJsxs(type, localizeGlobalJsxProps(props), key);
