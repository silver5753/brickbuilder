"""Build once, then exercise non-editable installations outside the checkout."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def checked(
    command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@dataclass(frozen=True)
class Installed:
    folder: Path
    python: Path
    command: Path
    env: dict[str, str]

    def run(
        self, *args: str | Path, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.command), *(str(a) for a in args)],
            cwd=self.folder,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        assert "Traceback" not in result.stderr
        return result


@pytest.fixture(scope="session")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("wheel")
    checked(["uv", "build", "--wheel", "--out-dir", str(destination)], cwd=ROOT)
    wheels = list(destination.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def install(wheel: Path, folder: Path, *, render: bool) -> Installed:
    venv = folder / "venv"
    checked(["uv", "venv", "--python", sys.executable, str(venv)], cwd=folder)
    bin_path = venv / ("Scripts" if os.name == "nt" else "bin")
    python = bin_path / ("python.exe" if os.name == "nt" else "python")
    checked(
        ["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
        cwd=folder,
    )
    if render:
        requirements = folder / "render-requirements.txt"
        requirements.write_text(
            checked(
                [
                    "uv",
                    "export",
                    "--locked",
                    "--extra",
                    "render",
                    "--no-dev",
                    "--no-emit-project",
                    "--format",
                    "requirements-txt",
                ],
                cwd=ROOT,
            ).stdout
        )
        checked(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            cwd=folder,
        )
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV"}
    }
    env["PYTHONNOUSERSITE"] = "1"
    origin = checked(
        [str(python), "-I", "-c", "import brickbuilder; print(brickbuilder.__file__)"],
        cwd=folder,
        env=env,
    ).stdout.strip()
    assert Path(origin).is_relative_to(venv)
    command = bin_path / ("brickbuilder.exe" if os.name == "nt" else "brickbuilder")
    return Installed(folder, python, command, env)


@pytest.fixture(scope="session")
def installed_core(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Installed:
    return install(wheel, tmp_path_factory.mktemp("installed-core"), render=False)


@pytest.fixture(scope="session")
def installed_render(
    wheel: Path, tmp_path_factory: pytest.TempPathFactory
) -> Installed:
    return install(wheel, tmp_path_factory.mktemp("installed-render"), render=True)
