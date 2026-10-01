export const hasEnabledEntitlement = (xml, key) => {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`<key>\\s*${escaped}\\s*</key>\\s*<true\\s*/>`).test(xml);
};

export const assertAudioInputEntitlement = (xml, target) => {
  if (!hasEnabledEntitlement(xml, "com.apple.security.device.audio-input")) {
    throw new Error(`Enabled audio-input entitlement is missing: ${target}`);
  }
};
