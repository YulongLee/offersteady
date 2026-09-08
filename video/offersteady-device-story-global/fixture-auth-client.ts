const account = {
  id: 'capture-user',
  displayName: 'Demo User',
  createdAtMs: 1719000000000,
  bindings: [],
};

export const authClient = {
  readStoredSession: () => ({accessToken: 'capture', refreshToken: 'capture', account}),
  readStoredAccount: () => account,
  restore: async () => ({accessToken: 'capture', refreshToken: 'capture', account}),
  clear: () => undefined,
  bootstrapPrototypeIdentity: () => undefined,
  logout: async () => undefined,
  sendSmsCode: async () => ({challengeId: 'capture', status: 'sent', provider: 'capture', expiresAtMs: 0, cooldownSeconds: 0, maskedPhone: '***'}),
  verifySmsLogin: async () => ({account}),
};
