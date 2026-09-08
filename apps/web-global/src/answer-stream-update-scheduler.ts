export interface AnswerStreamUpdateSchedulerOptions<T> {
  readonly apply: (update: T) => void;
  readonly isFirstVisible: (update: T) => boolean;
  readonly delayMs?: number;
  readonly schedule?: (callback: () => void, delayMs: number) => number;
  readonly cancel?: (timer: number) => void;
}

export const createAnswerStreamUpdateScheduler = <T>({
  apply,
  isFirstVisible,
  delayMs = 100,
  schedule = (callback, delay) => window.setTimeout(callback, delay),
  cancel = timer => window.clearTimeout(timer),
}: AnswerStreamUpdateSchedulerOptions<T>) => {
  let pending: T | null = null;
  let timer: number | null = null;
  let firstVisibleApplied = false;

  const flush = () => {
    if (timer !== null) cancel(timer);
    timer = null;
    if (pending === null) return;
    const update = pending;
    pending = null;
    apply(update);
  };

  const push = (update: T, terminal = false) => {
    if (!firstVisibleApplied && isFirstVisible(update)) {
      firstVisibleApplied = true;
      if (timer !== null) cancel(timer);
      timer = null;
      pending = null;
      apply(update);
      return;
    }
    pending = update;
    if (terminal) flush();
    else if (timer === null) timer = schedule(flush, delayMs);
  };

  const dispose = () => {
    if (timer !== null) cancel(timer);
    timer = null;
    pending = null;
  };

  return { push, flush, dispose };
};
