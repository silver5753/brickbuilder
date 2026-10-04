"""Immutable authored results shared by execution stages; no project assumptions."""

from dataclasses import dataclass, replace
import re

from .assembly import AuthoredModel
from .model import Model, reference_name


def authored(value: Model | AuthoredModel) -> AuthoredModel:
    if isinstance(value, AuthoredModel):
        return replace(
            value,
            attachments=tuple(value.attachments),
            connections=tuple(value.connections),
            requirements=tuple((key, tuple(ids)) for key, ids in value.requirements),
        )
    if isinstance(value, Model):
        return AuthoredModel(value, (), (), ())
    raise ValueError("Builder must return Model, AuthoredModel or BuildResult")


@dataclass(frozen=True)
class BuildResult:
    primary: Model | AuthoredModel
    poses: tuple[tuple[str, Model | AuthoredModel], ...] = ()

    def __post_init__(self) -> None:
        primary = authored(self.primary)
        object.__setattr__(self, "primary", primary)
        poses = tuple((name, authored(value)) for name, value in self.poses)
        object.__setattr__(self, "poses", poses)
        names = [name for name, _ in poses]
        if len(set(names)) != len(names) or any(
            not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", name) or name == "default"
            for name in names
        ):
            raise ValueError("Poses require unique safe names other than default")
        identities = self._identities(primary)
        for name, pose in poses:
            if self._identities(pose) != identities:
                raise ValueError(
                    f"Pose {name} changes instance identities or inventory; build a separate revision instead"
                )

    @staticmethod
    def _identities(value: AuthoredModel) -> dict[str, tuple[str, int]]:
        return {
            p.instance_id: (reference_name(p.reference), p.colour)
            for p in value.model.parts
        }

    def models(self) -> tuple[tuple[str, AuthoredModel], ...]:
        return (
            ("default", authored(self.primary)),
            *((name, authored(value)) for name, value in self.poses),
        )
