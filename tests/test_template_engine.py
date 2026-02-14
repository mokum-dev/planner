"""Tests for template engine core utilities."""

from __future__ import annotations

import unittest

from planner.template_engine import (
    Rect,
    RenderContext,
    TemplateParamSpec,
    TemplateRegistry,
    TemplateSpec,
    parse_param_pairs,
    resolve_template_params,
)


class _DummyBlock:
    def render(self, ctx: RenderContext, rect: Rect) -> None:  # pragma: no cover - contract stub
        _ = (ctx, rect)


def _dummy_build(params: dict[str, object]) -> _DummyBlock:
    _ = params
    return _DummyBlock()


class TemplateRegistryTests(unittest.TestCase):
    def test_registry_resolves_aliases(self) -> None:
        registry = TemplateRegistry()
        spec = TemplateSpec(
            template_id="example",
            title="Example",
            description="Example template.",
            build=_dummy_build,
            aliases=("legacy-example",),
        )
        registry.register(spec)
        self.assertIs(registry.get("example"), spec)
        self.assertIs(registry.get("legacy-example"), spec)

    def test_registry_rejects_duplicate_alias(self) -> None:
        registry = TemplateRegistry()
        registry.register(
            TemplateSpec(
                template_id="one",
                title="One",
                description="One template.",
                build=_dummy_build,
                aliases=("alias",),
            )
        )
        with self.assertRaises(ValueError):
            registry.register(
                TemplateSpec(
                    template_id="two",
                    title="Two",
                    description="Two template.",
                    build=_dummy_build,
                    aliases=("alias",),
                )
            )

    def test_registry_resolves_alias_with_surrounding_whitespace(self) -> None:
        registry = TemplateRegistry()
        spec = TemplateSpec(
            template_id="example",
            title="Example",
            description="Example template.",
            build=_dummy_build,
            aliases=("  legacy-example  ",),
        )
        registry.register(spec)
        self.assertIs(registry.get("legacy-example"), spec)

    def test_registry_rejects_duplicate_alias_after_whitespace_normalization(self) -> None:
        registry = TemplateRegistry()
        registry.register(
            TemplateSpec(
                template_id="one",
                title="One",
                description="One template.",
                build=_dummy_build,
                aliases=("  alias  ",),
            )
        )
        with self.assertRaises(ValueError):
            registry.register(
                TemplateSpec(
                    template_id="two",
                    title="Two",
                    description="Two template.",
                    build=_dummy_build,
                    aliases=("alias",),
                )
            )


class ParameterParsingTests(unittest.TestCase):
    def test_parse_param_pairs_rejects_missing_separator(self) -> None:
        with self.assertRaises(ValueError):
            parse_param_pairs(["notes_fill"])

    def test_resolve_template_params_applies_defaults_and_raw_params(self) -> None:
        spec = TemplateSpec(
            template_id="notes",
            title="Notes",
            description="Notes template.",
            build=_dummy_build,
            params=(
                TemplateParamSpec(
                    key="notes_fill",
                    value_type=str,
                    description="Fill type.",
                    default="lines",
                    choices=("lines", "grid"),
                ),
                TemplateParamSpec(
                    key="checklist_rows",
                    value_type=int,
                    description="Rows.",
                    min_value=1,
                ),
            ),
        )

        resolved = resolve_template_params(
            spec=spec,
            raw_params={
                "checklist_rows": "4",
                "notes_fill": "grid",
            },
        )
        self.assertEqual(resolved["notes_fill"], "grid")
        self.assertEqual(resolved["checklist_rows"], 4)

    def test_resolve_template_params_rejects_unknown_param(self) -> None:
        spec = TemplateSpec(
            template_id="simple",
            title="Simple",
            description="Simple template.",
            build=_dummy_build,
            params=(),
        )
        with self.assertRaises(ValueError):
            resolve_template_params(spec=spec, raw_params={"unknown": "1"})
