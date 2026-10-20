

import functools
import inspect
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, Union

from rich.console import Console
from rich.logging import RichHandler

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Context variables for distributed tracing
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")

# Sensitive key patterns to redact
SENSITIVE_PATTERNS = {
    "password", "secret", "token", "api_key", "apikey", "access_token",
    "refresh_token", "authorization", "auth", "credential", "private_key"
}

def strip_markup(text: str) -> str:
    """Strips console markup tags for clean file and JSON persistence using Rich's parser."""
    if not isinstance(text, str):
        return text
    try:
        from rich.text import Text
        return Text.from_markup(text).plain
    except Exception:
        return text


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """Set the trace/correlation ID for the current context. Generates UUID if None."""
    tid = trace_id or str(uuid.uuid4())
    _trace_id_ctx.set(tid)
    return tid


def get_trace_id() -> str:
    """Retrieve the trace/correlation ID for the current context."""
    return _trace_id_ctx.get()


def set_user_id(user_id: str) -> None:
    """Set the user ID for the current async or thread context."""
    _user_id_ctx.set(user_id)


def get_user_id() -> str:
    """Retrieve the user ID for the current context."""
    return _user_id_ctx.get()


def clear_context() -> None:
    """Reset trace and user context variables."""
    _trace_id_ctx.set("-")
    _user_id_ctx.set("-")


@contextmanager
def trace_scope(trace_id: Optional[str] = None, user_id: Optional[str] = None) -> Generator[str, None, None]:
    """
    Context manager to temporarily set trace_id and/or user_id for a block of code.
    Resets the context when the block exits.
    """
    tid = trace_id or str(uuid.uuid4())
    token_trace = _trace_id_ctx.set(tid)
    token_user = _user_id_ctx.set(user_id) if user_id else None
    try:
        yield tid
    finally:
        _trace_id_ctx.reset(token_trace)
        if token_user:
            _user_id_ctx.reset(token_user)


def sanitize_data(data: Any, max_length: int = 500) -> Any:
    """Recursively sanitize sensitive fields and truncate large payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            key_str = str(k).lower()
            if any(pattern in key_str for pattern in SENSITIVE_PATTERNS):
                sanitized[k] = "******"
            else:
                sanitized[k] = sanitize_data(v, max_length)
        return sanitized
    elif isinstance(data, (list, tuple, set)):
        return [sanitize_data(item, max_length) for item in data]
    elif isinstance(data, str):
        if len(data) > max_length:
            return data[:max_length] + f"... [truncated {len(data) - max_length} chars]"
        return data
    elif isinstance(data, (int, float, bool, type(None))):
        return data
    else:
        s = repr(data)
        if len(s) > max_length:
            return s[:max_length] + "... [truncated]"
        return s


class ContextFilter(logging.Filter):
    """Filter that injects context variables (trace_id, user_id) into the LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = getattr(record, "trace_id", _trace_id_ctx.get())
        record.user_id = getattr(record, "user_id", _user_id_ctx.get())
        return True


class PlainFileFormatter(logging.Formatter):
    """Clean text formatter for file logging without rich console tags."""

    def format(self, record: logging.LogRecord) -> str:
        orig_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = strip_markup(record.msg)
        try:
            return super().format(record)
        finally:
            record.msg = orig_msg


class JSONLogFormatter(logging.Formatter):
    """Production-grade structured JSON formatter for centralized logging aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        clean_msg = strip_markup(raw_msg)

        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": clean_msg,
            "trace_id": getattr(record, "trace_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "source": {
                "file": record.pathname,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            },
            "process": {
                "pid": record.process,
                "thread_name": record.threadName,
            },
        }

        # Include custom extra fields if provided
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "trace_id", "user_id",
            "asctime", "taskName",
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extras:
            log_entry["extra"] = sanitize_data(extras)

        # Include formatted exception if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "stacktrace": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str)


def _resolve_logs_dir() -> Path:
    """Resolve and create the logs folder at the backend root."""
    env_log_dir = os.getenv("LOG_DIR")
    if env_log_dir:
        logs_dir = Path(env_log_dir).resolve()
    else:
        # Default: <backend>/logs
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parents[2]
        logs_dir = backend_dir / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


# Global state tracking to guarantee idempotent handler configuration
_LOGGING_INITIALIZED = False
_LOGS_DIR: Optional[Path] = None


def setup_enterprise_logging(
    app_name: str = "researchos",
    log_level: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configures and initializes enterprise multi-target logging:
    1. Console: RichHandler (colored, formatted, syntax-highlighted)
    2. logs/app.log: General application logs (RotatingFileHandler)
    3. logs/error.log: WARNING, ERROR, and CRITICAL logs only (RotatingFileHandler)
    4. logs/app.json.log: Machine-readable JSON lines for log aggregators (RotatingFileHandler)
    """
    global _LOGGING_INITIALIZED, _LOGS_DIR

    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, log_level, logging.INFO)
    logs_dir = _resolve_logs_dir()
    _LOGS_DIR = logs_dir

    root_logger = logging.getLogger(app_name)
    root_logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers on multiple imports
    if not _LOGGING_INITIALIZED:
        context_filter = ContextFilter()

        # -------------------------------------------------------------
        # 1. Console Handler (Rich)
        # -------------------------------------------------------------
        console = Console(file=sys.stdout, force_terminal=True)
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_level=True,
            show_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            markup=True,
        )
        rich_handler.setLevel(numeric_level)
        rich_handler.addFilter(context_filter)
        rich_fmt = logging.Formatter(fmt="[trace:%(trace_id)s] %(message)s")
        rich_handler.setFormatter(rich_fmt)
        root_logger.addHandler(rich_handler)

        # -------------------------------------------------------------
        # 2. General File Handler (logs/app.log)
        # -------------------------------------------------------------
        app_log_path = logs_dir / "app.log"
        app_file_handler = RotatingFileHandler(
            filename=app_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        app_file_handler.setLevel(logging.DEBUG)  # Captures DEBUG and above to file
        app_file_handler.addFilter(context_filter)
        text_formatter = PlainFileFormatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s:%(funcName)s:%(lineno)d] | trace=%(trace_id)s user=%(user_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        app_file_handler.setFormatter(text_formatter)
        root_logger.addHandler(app_file_handler)

        # -------------------------------------------------------------
        # 3. Error-only File Handler (logs/error.log)
        # -------------------------------------------------------------
        error_log_path = logs_dir / "error.log"
        error_file_handler = RotatingFileHandler(
            filename=error_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_file_handler.setLevel(logging.WARNING)  # Captures WARNING, ERROR, CRITICAL
        error_file_handler.addFilter(context_filter)
        error_file_handler.setFormatter(text_formatter)
        root_logger.addHandler(error_file_handler)

        # -------------------------------------------------------------
        # 4. Structured JSON File Handler (logs/app.json.log)
        # -------------------------------------------------------------
        json_log_path = logs_dir / "app.json.log"
        json_file_handler = RotatingFileHandler(
            filename=json_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        json_file_handler.setLevel(logging.DEBUG)
        json_file_handler.addFilter(context_filter)
        json_file_handler.setFormatter(JSONLogFormatter())
        root_logger.addHandler(json_file_handler)

        root_logger.propagate = False
        _LOGGING_INITIALIZED = True

    return root_logger


class BoundLoggerAdapter(logging.LoggerAdapter):
    """LoggerAdapter providing .bind(**kwargs) and .get_logger(name) for contextual logging."""

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = dict(self.extra)
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
        kwargs["extra"] = extra
        return msg, kwargs

    def bind(self, **kwargs: Any) -> "BoundLoggerAdapter":
        merged = {**self.extra, **kwargs}
        return BoundLoggerAdapter(self.logger, merged)

    def get_logger(self, name: Optional[str] = None) -> "BoundLoggerAdapter":
        return get_logger(name)


def get_logger(name: Optional[str] = None) -> BoundLoggerAdapter:
    """
    Get a configured logger instance with the specified module or component name.
    If name is None, returns the primary root logger.
    """
    base_name = "researchos"
    if not _LOGGING_INITIALIZED:
        setup_enterprise_logging(app_name=base_name)

    if not name or name == base_name:
        raw_logger = logging.getLogger(base_name)
    elif not name.startswith(f"{base_name}."):
        full_name = f"{base_name}.{name}"
        raw_logger = logging.getLogger(full_name)
        raw_logger.setLevel(logging.getLogger(base_name).level)
    else:
        raw_logger = logging.getLogger(name)
        raw_logger.setLevel(logging.getLogger(base_name).level)

    return BoundLoggerAdapter(raw_logger, {})


# Default system logger instance
logger = get_logger("core")



# -----------------------------------------------------------------------------
# Function Execution Logging Decorator (Production Grade)
# -----------------------------------------------------------------------------

def log_execution(
    level: str = "INFO",
    log_args: bool = True,
    log_result: bool = False,
    time_execution: bool = True,
    reraise: bool = True,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable[[F], F]:
    
    log_level_num = getattr(logging, level.upper(), logging.INFO)

    def decorator(func: F) -> F:
        log = logger_instance or get_logger(func.__module__)
        func_name = f"{func.__qualname__}"

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                sanitized_kwargs = sanitize_data(kwargs) if log_args else {}
                sanitized_args = sanitize_data(args) if log_args else ()

                log.log(
                    log_level_num,
                    f"Entering async [bold cyan]{func_name}[/bold cyan]"
                    + (f" with args={sanitized_args} kwargs={sanitized_kwargs}" if log_args else ""),
                    extra={"event": "function_start", "function": func_name},
                )
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000.0

                    msg = f"Completed async [bold green]{func_name}[/bold green]"
                    if time_execution:
                        msg += f" in {duration_ms:.2f}ms"
                    if log_result:
                        msg += f" -> result={sanitize_data(result)}"

                    log.log(
                        log_level_num,
                        msg,
                        extra={"event": "function_end", "function": func_name, "duration_ms": duration_ms},
                    )
                    return result
                except Exception as ex:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    log.error(
                        f"Failed in async [bold red]{func_name}[/bold red] after {duration_ms:.2f}ms: {ex}",
                        exc_info=True,
                        extra={"event": "function_error", "function": func_name, "duration_ms": duration_ms},
                    )
                    if reraise:
                        raise

            return async_wrapper  # type: ignore

        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                sanitized_kwargs = sanitize_data(kwargs) if log_args else {}
                sanitized_args = sanitize_data(args) if log_args else ()

                log.log(
                    log_level_num,
                    f"Entering [bold cyan]{func_name}[/bold cyan]"
                    + (f" with args={sanitized_args} kwargs={sanitized_kwargs}" if log_args else ""),
                    extra={"event": "function_start", "function": func_name},
                )
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000.0

                    msg = f"Completed [bold green]{func_name}[/bold green]"
                    if time_execution:
                        msg += f" in {duration_ms:.2f}ms"
                    if log_result:
                        msg += f" -> result={sanitize_data(result)}"

                    log.log(
                        log_level_num,
                        msg,
                        extra={"event": "function_end", "function": func_name, "duration_ms": duration_ms},
                    )
                    return result
                except Exception as ex:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    log.error(
                        f"Failed in [bold red]{func_name}[/bold red] after {duration_ms:.2f}ms: {ex}",
                        exc_info=True,
                        extra={"event": "function_error", "function": func_name, "duration_ms": duration_ms},
                    )
                    if reraise:
                        raise

            return sync_wrapper  # type: ignore

    return decorator


# Alias for convenience
log_function = log_execution


# -----------------------------------------------------------------------------
# Enterprise Compliance & Operational Logging Helpers
# -----------------------------------------------------------------------------

def log_audit(
    action: str,
    actor_id: str,
    resource: str,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> None:
    """Log security and audit compliance events."""
    log = logger_instance or get_logger("audit")
    event = {
        "audit_event": action,
        "actor_id": actor_id,
        "resource": resource,
        "status": status,
        "details": sanitize_data(details or {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.info(f"AUDIT | {actor_id} performed {action} on {resource} -> {status}", extra={"audit": event})


def log_metric(
    metric_name: str,
    value: Union[int, float],
    unit: str = "ms",
    tags: Optional[Dict[str, str]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> None:
    """Log performance and operational metrics."""
    log = logger_instance or get_logger("metrics")
    metric_data = {
        "metric": metric_name,
        "value": value,
        "unit": unit,
        "tags": tags or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.info(f"METRIC | {metric_name}={value}{unit} tags={tags or {}}", extra={"metric": metric_data})
