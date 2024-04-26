from contextlib import contextmanager
from logging import getLogger

from packit.tracing.spans import SpanKind

logger = getLogger(__name__)


def make_tracer(callback):
    @contextmanager
    def trace(name: str, kind: str | SpanKind = SpanKind.TASK):
        if isinstance(kind, SpanKind):
            kind = kind.value

        span_name = f"{kind}.{name}"
        logger.debug("tracing span %s", span_name)

        def report_args(*args, **kwargs):
            logger.debug("reporting args %s %s", args, kwargs)
            callback(span=span_name, args=args, kwargs=kwargs)

        def report_output(res):
            logger.debug("reporting output %s", res)
            callback(span=span_name, result=res)

        callback(span=span_name)
        yield report_args, report_output
        # callback(done=True)

    return trace
