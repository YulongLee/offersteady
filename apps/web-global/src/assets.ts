import type { ProductAssetEntry, ProductAssetManifest } from "@offersteady/protocol";

export const productAssets: ProductAssetManifest = {
  version: 1,
  entries: [
    { id: "brand.app-icon", category: "brand", path: "/assets/brand/app-icon-96.png", purpose: "Global application icon", alt: "OfferSteady application icon", width: 96, height: 96, sha256: "a60444614a351147c173fd2686b6eaf9eeb0a1297747c787cfb3bdb1b8967a85", version: 3, public: true },
    { id: "brand.favicon", category: "brand", path: "/assets/brand/favicon.png", purpose: "Global browser icon", alt: "OfferSteady", width: 64, height: 64, sha256: "d05ede3067dd27965ed4a572d5f7b4538385f68479c174c18ffb2a421605a686", version: 2, public: true },
  ],
};

export const resolveAsset = (id: string, nowMs = Date.now(), manifest = productAssets): ProductAssetEntry | null =>
  manifest.entries.find((item) => item.id === id
    && item.public
    && (!item.expiresAtMs || item.expiresAtMs > nowMs)
    && /^[a-f0-9]{64}$/i.test(item.sha256)) ?? null;

export const assetUrl = (id: string, fallback = "/assets/brand/app-icon-96.png") =>
  resolveAsset(id)?.path ?? fallback;
