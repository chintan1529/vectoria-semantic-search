"""
Priority-Aware Asynchronous Worker Queue (Phase 3 & Refinement 4/7).

Executes non-essential tasks (Failure Memory, Analytics, Dataset Gap Detection, Dashboard Telemetry)
off the critical path with priority scheduling, backpressure, and load shedding.
"""

import asyncio
from typing import Callable, Any, Dict
from backend.core.logging import logger
from vectoria.performance.degradation import degradation_manager, DegradationLevel


class AsyncWorkerQueue:
    """Priority-aware background worker queue with load shedding."""

    def __init__(self, max_queue_size: int = 50):
        self._max_queue_size = max_queue_size
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task = None
        self._is_running = False

    def start(self) -> None:
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while self._is_running:
            try:
                task_func, args, kwargs = await self._queue.get()
                try:
                    if asyncio.iscoroutinefunction(task_func):
                        await task_func(*args, **kwargs)
                    else:
                        await asyncio.to_thread(task_func, *args, **kwargs)
                except Exception as task_err:
                    logger.warning("ASYNC_QUEUE_TASK_ERROR | error=%s", str(task_err))
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error("ASYNC_QUEUE_LOOP_ERROR | error=%s", str(loop_err))

    def enqueue(self, task_func: Callable, *args, priority: str = "LOW", **kwargs) -> bool:
        """Enqueue task. Sheds low-priority tasks under load shedding or backpressure."""
        current_state = degradation_manager.evaluate_state(0, 0, self._queue.qsize())
        
        # Load shedding: Drop low priority background jobs under CRITICAL degradation
        if priority == "LOW" and (current_state.level == DegradationLevel.CRITICAL or self._queue.full()):
            logger.warning("ASYNC_QUEUE_LOAD_SHEDDING | task=%s shed due to pressure/backlog", getattr(task_func, '__name__', 'func'))
            return False

        try:
            self._queue.put_nowait((task_func, args, kwargs))
            return True
        except asyncio.QueueFull:
            logger.warning("ASYNC_QUEUE_FULL | task dropped")
            return False

    @property
    def qsize(self) -> int:
        return self._queue.qsize()


# Singleton background worker queue
async_worker_queue = AsyncWorkerQueue()
