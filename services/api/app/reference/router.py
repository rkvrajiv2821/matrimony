"""Public reference data for forms: option codes, locations and community taxonomy.

Locations and communities are addressed by stable `code`s; numeric ids stay internal.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.common.errors import NotFound
from app.profiles.options import ALL_OPTIONS, MAX_HEIGHT_CM, MIN_AGE, MIN_HEIGHT_CM
from app.reference.models import CommunityTaxonomy, Location, LocationType, TaxonomyType
from app.security.deps import DB

router = APIRouter(prefix="/reference", tags=["reference"])

CACHE = "public, max-age=3600"


class OptionsOut(BaseModel):
    options: dict[str, list[str]]
    min_age: int
    min_height_cm: int
    max_height_cm: int


class LocationOut(BaseModel):
    code: str
    type: LocationType
    name_en: str
    name_ta: str
    parent_code: str | None


class CommunityOut(BaseModel):
    code: str
    type: TaxonomyType
    label_en: str
    label_ta: str
    parent_code: str | None


@router.get("/options", response_model=OptionsOut)
async def options(response: Response) -> OptionsOut:
    response.headers["Cache-Control"] = CACHE
    return OptionsOut(
        options={k: [m.value for m in enum] for k, enum in ALL_OPTIONS.items()},
        min_age=MIN_AGE,
        min_height_cm=MIN_HEIGHT_CM,
        max_height_cm=MAX_HEIGHT_CM,
    )


@router.get("/locations", response_model=list[LocationOut])
async def locations(
    db: DB,
    response: Response,
    parent: Annotated[str | None, Query(max_length=50, description="Parent location code")] = None,
    type: Annotated[LocationType | None, Query()] = None,
) -> list[LocationOut]:
    parent_loc = aliased(Location)
    stmt = (
        select(Location, parent_loc.code)
        .outerjoin(parent_loc, parent_loc.id == Location.parent_id)
        .where(Location.active.is_(True))
        .order_by(Location.name_en)
    )
    if parent is not None:
        pid = await db.scalar(select(Location.id).where(Location.code == parent))
        if pid is None:
            raise NotFound()
        stmt = stmt.where(Location.parent_id == pid)
    elif type is None:
        stmt = stmt.where(Location.parent_id.is_(None))
    if type is not None:
        stmt = stmt.where(Location.type == type.value)
    response.headers["Cache-Control"] = CACHE
    return [
        LocationOut(
            code=loc.code,
            type=LocationType(loc.type),
            name_en=loc.name_en,
            name_ta=loc.name_ta,
            parent_code=pcode,
        )
        for loc, pcode in (await db.execute(stmt)).all()
    ]


@router.get("/community", response_model=list[CommunityOut])
async def community(db: DB, response: Response) -> list[CommunityOut]:
    parent = aliased(CommunityTaxonomy)
    rows = await db.execute(
        select(CommunityTaxonomy, parent.code)
        .outerjoin(parent, parent.id == CommunityTaxonomy.parent_id)
        .where(CommunityTaxonomy.active.is_(True))
        .order_by(CommunityTaxonomy.type, CommunityTaxonomy.sort_order)
    )
    response.headers["Cache-Control"] = CACHE
    return [
        CommunityOut(
            code=c.code,
            type=TaxonomyType(c.type),
            label_en=c.label_en,
            label_ta=c.label_ta,
            parent_code=pcode,
        )
        for c, pcode in rows.all()
    ]
