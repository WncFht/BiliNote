from threading import Lock
from typing import Any, Callable


class SerialTaskExecutor:
    """Serialize note-generation tasks within the current process."""

    def __init__(self):
        self._lock = Lock()

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return fn(*args, **kwargs)

    def shutdown(self, wait: bool = True):
        del wait


# Keep the upstream export name for compatibility.
ConcurrentTaskExecutor = SerialTaskExecutor
task_serial_executor = SerialTaskExecutor()
