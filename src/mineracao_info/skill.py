from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class SkillRuntime:
    markdown: str
    sha256: str
    rules: dict
    version: str


def load_skill(skill_path: Path, runtime_path: Path) -> SkillRuntime:
    markdown = skill_path.read_text(encoding="utf-8")
    sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    rules = yaml.safe_load(runtime_path.read_text(encoding="utf-8")) or {}
    return SkillRuntime(
        markdown=markdown,
        sha256=sha,
        rules=rules,
        version=str(rules.get("version", "unknown")),
    )
