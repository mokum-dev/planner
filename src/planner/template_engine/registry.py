"""Template registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import TemplateSpec


@dataclass
class TemplateRegistry:
    """In-memory registry of template specs."""

    _specs: dict[str, TemplateSpec] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)

    def register(self, spec: TemplateSpec) -> None:
        template_id = spec.template_id.strip()
        if not template_id:
            msg = "template_id cannot be empty."
            raise ValueError(msg)
        if template_id in self._specs:
            msg = f"template '{template_id}' is already registered."
            raise ValueError(msg)
        if template_id in self._aliases:
            msg = f"template id '{template_id}' conflicts with an existing alias."
            raise ValueError(msg)

        alias_keys: list[str] = []
        for alias in spec.aliases:
            alias_key = alias.strip()
            if not alias_key:
                msg = "template alias cannot be empty."
                raise ValueError(msg)
            if alias_key == template_id:
                msg = f"alias '{alias_key}' duplicates template id '{template_id}'."
                raise ValueError(msg)
            if alias_key in self._specs or alias_key in self._aliases:
                msg = f"template alias '{alias_key}' is already registered."
                raise ValueError(msg)
            alias_keys.append(alias_key)

        self._specs[template_id] = spec
        for alias_key in alias_keys:
            self._aliases[alias_key] = template_id

    def register_many(self, specs: tuple[TemplateSpec, ...] | list[TemplateSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def resolve_id(self, template: str) -> str:
        if template in self._specs:
            return template
        if template in self._aliases:
            return self._aliases[template]
        valid = ", ".join(sorted(self.template_ids()))
        msg = f"unknown template '{template}'. Valid templates: {valid}."
        raise ValueError(msg)

    def get(self, template: str) -> TemplateSpec:
        return self._specs[self.resolve_id(template)]

    def list_specs(self) -> tuple[TemplateSpec, ...]:
        return tuple(self._specs.values())

    def template_ids(self) -> tuple[str, ...]:
        return tuple(self._specs)
