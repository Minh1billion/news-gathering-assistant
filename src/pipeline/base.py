import threading
from abc import ABC, abstractmethod


class PipelineStep(ABC):
    @abstractmethod
    def run(self, cancel_event: threading.Event | None = None): ...