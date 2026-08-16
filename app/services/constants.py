"""Small mappings between Settings-facing values and API-facing values."""

import re
from typing import Tuple

_LEADING_DIGITS_RE = re.compile(r"^(\d+)(.*)$")


def team_sort_key(number: str) -> Tuple[int, str]:
    """Sort team numbers numerically-then-alphabetically (e.g. "2A" < "10B")."""
    match = _LEADING_DIGITS_RE.match(number or "")
    if match:
        return int(match.group(1)), match.group(2)
    return 0, number or ""

# Grade code (used in Settings/localStorage) -> Team.grade enum string.
GRADE_TO_FULL = {
    "ES": "Elementary School",
    "MS": "Middle School",
    "HS": "High School",
}

# Grade code -> SkillsGradeLevel string (world skills endpoint uses a
# different set of strings than Team.grade).
GRADE_TO_SKILLS_LEVEL = {
    "ES": "Elementary",
    "MS": "Middle School",
    "HS": "High School",
}

# Program abbreviation -> dashboard table key (Active Teams Dashboard).
PROGRAM_TABLE_KEY = {
    "VIQRC": "IQ",
    "V5RC": "V5",
}

# Fixed display order for World Skills Dashboard program+grade groups.
WORLD_SKILLS_GROUP_ORDER = [
    ("VIQRC", "ES"),
    ("VIQRC", "MS"),
    ("V5RC", "MS"),
    ("V5RC", "HS"),
]
_WORLD_SKILLS_GROUP_INDEX = {key: i for i, key in enumerate(WORLD_SKILLS_GROUP_ORDER)}


def world_skills_group_sort_key(program: str, grade: str) -> int:
    return _WORLD_SKILLS_GROUP_INDEX.get((program, grade), len(WORLD_SKILLS_GROUP_ORDER))
