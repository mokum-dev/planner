"""Template parameter parsing and validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import TemplateParamSpec, TemplateSpec

BOOL_TRUE = {"1", "true", "yes", "on"}
BOOL_FALSE = {"0", "false", "no", "off"}


def parse_param_pairs(pairs: Sequence[str] | None) -> dict[str, str]:
    """Parse repeatable key=value CLI pairs into a dict."""
    parsed: dict[str, str] = {}
    for raw_pair in pairs or ():
        if "=" not in raw_pair:
            msg = f"invalid --param '{raw_pair}'. Expected key=value."
            raise ValueError(msg)
        raw_key, raw_value = raw_pair.split("=", 1)
        key = raw_key.strip()
        value = raw_value.strip()
        if not key:
            msg = f"invalid --param '{raw_pair}'. Key cannot be empty."
            raise ValueError(msg)
        parsed[key] = value
    return parsed


def _spec_by_key(spec: TemplateSpec) -> dict[str, TemplateParamSpec]:
    indexed: dict[str, TemplateParamSpec] = {}
    for param in spec.params:
        for key in param.all_keys():
            if key in indexed:
                msg = f"duplicate parameter key mapping '{key}' in template '{spec.template_id}'."
                raise ValueError(msg)
            indexed[key] = param
    return indexed


def _coerce_value(param: TemplateParamSpec, raw_value: Any, *, template_id: str) -> Any:
    key = param.key

    if param.value_type is bool:
        if isinstance(raw_value, bool):
            coerced = raw_value
        else:
            normalized = str(raw_value).strip().lower()
            if normalized in BOOL_TRUE:
                coerced = True
            elif normalized in BOOL_FALSE:
                coerced = False
            else:
                msg = (
                    f"invalid value '{raw_value}' for '{key}' in template '{template_id}'. "
                    "Expected a boolean (true/false)."
                )
                raise ValueError(msg)
    elif param.value_type is int:
        try:
            coerced = int(raw_value)
        except (TypeError, ValueError) as exc:
            msg = (
                f"invalid value '{raw_value}' for '{key}' in template '{template_id}'. "
                "Expected an integer."
            )
            raise ValueError(msg) from exc
    elif param.value_type is float:
        try:
            coerced = float(raw_value)
        except (TypeError, ValueError) as exc:
            msg = (
                f"invalid value '{raw_value}' for '{key}' in template '{template_id}'. "
                "Expected a float."
            )
            raise ValueError(msg) from exc
    elif param.value_type is str:
        coerced = str(raw_value)
    else:
        msg = f"unsupported param type '{param.value_type}' for '{key}' in '{template_id}'."
        raise ValueError(msg)

    if param.choices and coerced not in param.choices:
        choices = ", ".join(str(choice) for choice in param.choices)
        msg = (
            f"invalid value '{coerced}' for '{key}' in template '{template_id}'. "
            f"Valid values: {choices}."
        )
        raise ValueError(msg)

    if (
        param.min_value is not None
        and isinstance(coerced, (int, float))
        and coerced < param.min_value
    ):
        msg = (
            f"invalid value '{coerced}' for '{key}' in template '{template_id}'. "
            f"Minimum allowed value is {param.min_value}."
        )
        raise ValueError(msg)
    if (
        param.max_value is not None
        and isinstance(coerced, (int, float))
        and coerced > param.max_value
    ):
        msg = (
            f"invalid value '{coerced}' for '{key}' in template '{template_id}'. "
            f"Maximum allowed value is {param.max_value}."
        )
        raise ValueError(msg)

    return coerced


def resolve_template_params(
    *,
    spec: TemplateSpec,
    raw_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve defaults and apply provided raw params."""
    indexed = _spec_by_key(spec)
    defaults: dict[str, Any] = {}
    required: set[str] = set()
    for param in spec.params:
        if param.has_default:
            defaults[param.key] = param.default
        if param.required:
            required.add(param.key)

    resolved = dict(defaults)

    for key, raw_value in (raw_params or {}).items():
        if raw_value is None:
            continue
        if key not in indexed:
            valid = ", ".join(param.key for param in spec.params)
            msg = (
                f"unknown parameter '{key}' for template '{spec.template_id}'. "
                f"Supported parameters: {valid}."
            )
            raise ValueError(msg)
        param = indexed[key]
        resolved[param.key] = _coerce_value(param, raw_value, template_id=spec.template_id)

    missing = sorted(key for key in required if key not in resolved)
    if missing:
        msg = (
            f"missing required parameter(s) for template "
            f"'{spec.template_id}': {', '.join(missing)}."
        )
        raise ValueError(msg)

    return resolved
