import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger("app.perf")

class PerformanceTracker:
    """Thread-safe and task-friendly tracker for measuring sub-operation latencies."""
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = time.perf_counter()
        self.metrics: Dict[str, float] = {}
        self.ttft: Optional[float] = None

    @contextmanager
    def measure(self, stage_name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.metrics[stage_name] = round(elapsed_ms, 1)

    def record_ttft(self):
        if self.ttft is None:
            self.ttft = round((time.perf_counter() - self.start_time) * 1000, 1)

    def finish(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        total_ms = round((time.perf_counter() - self.start_time) * 1000, 1)
        self.metrics["total_ms"] = total_ms
        if self.ttft is not None:
            self.metrics["ttft_ms"] = self.ttft
        
        # Format clean log line: [PERF] Operation=... | stage1=...ms | stage2=...ms | Total=...ms
        stages_str = " | ".join(f"{k}={v}ms" for k, v in self.metrics.items() if k != "total_ms")
        extra_str = f" | {extra}" if extra else ""
        logger.info(f"[PERF] {self.operation_name} -> {stages_str} | Total={total_ms}ms{extra_str}")
        return self.metrics

@contextmanager
def perf_timer(name: str):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"[PERF] {name}: {elapsed_ms:.1f}ms")
