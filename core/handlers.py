import asyncio
import logging
import signal
from asyncio import Task


def tasks_handlers(*tasks) -> None:
    def stop_callback(sig: signal.Signals) -> None:
        task: Task
        for task in tasks:
            logging.warning("Received %s signal for task %s", sig.name, task.get_name())
            if not task.cancelled():
                task.cancel(f'Cancel task {task.get_name()}')

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_callback, signal.SIGTERM)
    loop.add_signal_handler(signal.SIGINT, stop_callback, signal.SIGINT)
