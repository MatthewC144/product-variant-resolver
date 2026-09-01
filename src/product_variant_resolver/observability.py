from __future__ import annotations

import time
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Any, Protocol


class Span(Protocol):
    """Subset shared by OpenTelemetry spans and the offline no-op span."""

    def set_attribute(self, key: str, value: Any) -> Any: ...
    def record_exception(self, exception: BaseException) -> Any: ...


class Tracer(Protocol):
    def start_as_current_span(self, name: str, **kwargs: Any) -> Any: ...


class NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exception: BaseException) -> None:
        return None


class NoOpTracer:
    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[NoOpSpan]:
        yield NoOpSpan()


NOOP_TRACER = NoOpTracer()


def get_tracer(enabled: bool) -> Tracer:
    """Return a configured OTel tracer or a dependency-free synchronous no-op.

    This does not install an exporter, start a worker, or perform I/O. Applications
    that opt in own SDK/provider/exporter configuration.
    """

    if not enabled:
        return NOOP_TRACER
    try:
        from opentelemetry import trace
    except (ImportError, ModuleNotFoundError):
        return NOOP_TRACER
    return trace.get_tracer("product_variant_resolver", "0.1.0")


@contextmanager
def observed_stage(
    tracer: Tracer,
    name: str,
    timings_ms: MutableMapping[str, float],
) -> Iterator[Span]:
    """Measure a synchronous stage and mirror failures to its current span."""

    started = time.perf_counter()
    with tracer.start_as_current_span(f"pvr.{name}") as span:
        try:
            yield span
        except Exception as error:
            span.set_attribute("pvr.error_type", type(error).__name__)
            span.record_exception(error)
            raise
        finally:
            elapsed = round((time.perf_counter() - started) * 1000, 4)
            timings_ms[name] = elapsed
            span.set_attribute("pvr.stage", name)
            span.set_attribute("pvr.duration_ms", elapsed)
