export interface ProtocolCompatibility {
  readonly serverVersion: string;
  readonly minimumCompanionVersion: string;
  readonly maximumCompanionVersionExclusive: string;
}

const parseMajor = (version: string): number | null => {
  const value = Number.parseInt(version.split(".")[0] ?? "", 10);
  return Number.isFinite(value) ? value : null;
};

export const isProtocolCompatible = (
  companionVersion: string,
  serverVersion: string,
): boolean => {
  const companionMajor = parseMajor(companionVersion);
  const serverMajor = parseMajor(serverVersion);
  return companionMajor !== null && companionMajor === serverMajor;
};

export const supportsSpeakerAwareTranscripts = (protocolVersion: string): boolean => {
  const major = parseMajor(protocolVersion);
  return major !== null && major >= 1;
};

export const supportsDualChannelRoleRouting = (protocolVersion: string): boolean => {
  const major = parseMajor(protocolVersion);
  return major !== null && major >= 1;
};

export const supportsAnswerCancellation = (protocolVersion: string): boolean => {
  const major = parseMajor(protocolVersion);
  return major !== null && major >= 1;
};
