/** One OS consent dialog at a time, including across renderer reloads. */
export const createMicrophonePermissionRequest = (
  status: () => string,
  ask: () => Promise<boolean>,
) => {
  let pending: Promise<boolean> | null = null;
  return (): Promise<boolean> => {
    if (pending) return pending;
    const current = status();
    if (current === "granted") return Promise.resolve(true);
    if (current === "denied" || current === "restricted") return Promise.resolve(false);
    pending = Promise.resolve().then(ask).finally(() => { pending = null; });
    return pending;
  };
};
