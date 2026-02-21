"""Template engine package."""

from .contracts import Block, Rect, RenderContext, TemplateParamSpec, TemplateSpec
from .params import parse_param_pairs, resolve_template_params
from .plugins import PLUGIN_API_VERSION, load_template_plugins
from .registry import TemplateRegistry

__all__ = [
    "PLUGIN_API_VERSION",
    "Block",
    "Rect",
    "RenderContext",
    "TemplateParamSpec",
    "TemplateRegistry",
    "TemplateSpec",
    "load_template_plugins",
    "parse_param_pairs",
    "resolve_template_params",
]
