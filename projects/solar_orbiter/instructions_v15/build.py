"""Instruction adapter: preserve the captured v15 CAD; never redesign it."""
from brickbuilder.ldraw import read_source
from brickbuilder.model import Model
from brickbuilder.project import Project

def build(project: Project) -> Model:
    return read_source(project.root / "model.ldr").document.model
