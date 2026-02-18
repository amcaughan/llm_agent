import json
import logging
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class Observer:
    logger: logging.Logger
    log_format: str
    max_field_chars: int

    def _normalize(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            out = value
        else:
            out = str(value)

        if isinstance(out, str) and len(out) > self.max_field_chars:
            return f"{out[:self.max_field_chars]}...<truncated>"
        return out

    def event(self, level: int, name: str, **fields: Any) -> None:
        payload = {"event": name}
        payload.update({k: self._normalize(v) for k, v in fields.items()})
        if self.log_format == "json":
            self.logger.log(level, json.dumps(payload, sort_keys=True))
            return

        pieces = [f"event={name}"]
        pieces.extend(f"{k}={payload[k]!r}" for k in sorted(fields.keys()))
        self.logger.log(level, " ".join(pieces))


def _resolve_level(level_name: str) -> int:
    return getattr(logging, level_name.upper(), logging.INFO)


def configure_observer(level_name: str, log_format: str, max_field_chars: int) -> Observer:
    logger = logging.getLogger("agent")
    logger.setLevel(_resolve_level(level_name))
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return Observer(
        logger=logger,
        log_format=log_format,
        max_field_chars=max_field_chars,
    )
