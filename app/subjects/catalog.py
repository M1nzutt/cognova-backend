from typing import Literal, get_args

SubjectStatus = Literal["active", "archived"]
SubjectDifficulty = Literal["easy", "medium", "hard"]
ColorBase = Literal[
    "blue",
    "violet",
    "pink",
    "rose",
    "orange",
    "amber",
    "green",
    "teal",
    "cyan",
    "slate",
]
ColorShade = Literal[100, 200, 300, 400, 500]
COLOR_BASES: tuple[str, ...] = get_args(ColorBase)
COLOR_SHADES: tuple[int, ...] = get_args(ColorShade)
