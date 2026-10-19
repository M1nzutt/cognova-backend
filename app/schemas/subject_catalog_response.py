from typing import Literal

from pydantic import BaseModel

from app.subjects.catalog import COLOR_BASES, COLOR_SHADES


class SubjectCatalogResponse(BaseModel):
    version: Literal[1] = 1
    color_bases: tuple[str, ...] = COLOR_BASES
    color_shades: tuple[int, ...] = COLOR_SHADES
