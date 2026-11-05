"""Bound physical provider close handshakes after logical detachment.

Only captured old connections are submitted here. Overload closes inline;
accepted work is never discarded or retried, including during shutdown.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import threading


class CnProviderCloseExecutor:
    def __init__(self, logger: logging.Logger, *, workers: int = 2, queue_max: int = 8):
        self._logger = logger
        self._condition = threading.Condition()
        self._slots = threading.BoundedSemaphore(workers + queue_max)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cn-provider-close")
        self._closed = False
        self._pending = self._completed = self._failed = self._inline = self._submitted = 0

    def close(self, operation):
        job = {"operation": operation, "claimed": False, "slot": False}
        with self._condition:
            self._pending += 1
            if not self._closed and self._slots.acquire(blocking=False):
                job["slot"] = True
                try:
                    self._pool.submit(self._run, job)
                    self._submitted += 1
                    return
                except Exception:
                    # Thread creation may fail after submit queued the work.
                    # Poison admission and claim this job exactly once below;
                    # a late queued invocation becomes a no-op.
                    self._closed = True
            self._inline += 1
        self._run(job)

    def _run(self, job):
        with self._condition:
            if job["claimed"]:
                return
            job["claimed"] = True
        try:
            job["operation"]()
        except Exception:
            with self._condition:
                self._failed += 1
            try:
                self._logger.warning('cn_provider_close_failed {"count":1}')
            except Exception:
                pass
        finally:
            if job["slot"]:
                self._slots.release()
            with self._condition:
                self._pending -= 1
                self._completed += 1
                self._condition.notify_all()

    def drain(self):
        with self._condition:
            self._condition.wait_for(lambda: self._pending == 0)

    def shutdown(self):
        with self._condition:
            self._closed = True
        self._pool.shutdown(wait=True)
        self.drain()

    def diagnostics(self):
        with self._condition:
            return {"pending": self._pending, "completed": self._completed,
                    "failed": self._failed, "inline": self._inline,
                    "submitted": self._submitted, "closed": int(self._closed)}
