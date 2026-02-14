"""Tests for template plugin loading."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from planner.template_engine import TemplateRegistry
from planner.template_engine.plugins import load_template_plugins


class TemplatePluginLoadingTests(unittest.TestCase):
    def test_load_template_plugin_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir)
            plugin_file = plugin_dir / "demo_plugin.py"
            plugin_file.write_text(
                """
from planner.template_engine import TemplateSpec

class _Block:
    def render(self, ctx, rect):
        pass

def _build(params):
    return _Block()

def register_templates(registry):
    registry.register(
        TemplateSpec(
            template_id="plugin-demo",
            title="Plugin Demo",
            description="Demo plugin template.",
            build=_build,
        )
    )
"""
            )

            sys.path.insert(0, str(plugin_dir))
            try:
                registry = TemplateRegistry()
                warnings = load_template_plugins(registry=registry, module_paths=("demo_plugin",))
                self.assertEqual(warnings, ())
                self.assertEqual(registry.get("plugin-demo").template_id, "plugin-demo")
            finally:
                sys.path.remove(str(plugin_dir))
                sys.modules.pop("demo_plugin", None)

    def test_load_template_plugin_reports_warning_for_bad_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir)
            plugin_file = plugin_dir / "bad_plugin.py"
            plugin_file.write_text("x = 1\n")

            sys.path.insert(0, str(plugin_dir))
            try:
                registry = TemplateRegistry()
                warnings = load_template_plugins(registry=registry, module_paths=("bad_plugin",))
                self.assertEqual(len(warnings), 1)
                self.assertIn("failed to load template plugin", warnings[0])
            finally:
                sys.path.remove(str(plugin_dir))
                sys.modules.pop("bad_plugin", None)

