"""Project-local authoring entry point. Review unfamiliar Python before executing."""

from brickbuilder.model import Model
from brickbuilder.project import Project


def build(project: Project) -> Model:
    """Return a flattened physical-part model with native IDs and rigid placements."""
    raise NotImplementedError(f"Author the {project.name} model from its brief first")
