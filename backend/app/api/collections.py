"""Collections API — save papers to named collections with notes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, CollectionPaper, Paper
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/collections", tags=["Collections"])


# ── Schemas ──────────────────────────────────────────────────

class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    is_public: bool = False


class AddPaperRequest(BaseModel):
    paper_id: int
    user_notes: str | None = None


class UpdateNotesRequest(BaseModel):
    user_notes: str


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool
    paper_count: int
    created_at: str


class CollectionDetailResponse(CollectionResponse):
    papers: list[dict]


# ── Endpoints ────────────────────────────────────────────────

@router.post("/", response_model=CollectionResponse, status_code=201)
async def create_collection(
    request: CreateCollectionRequest, db: AsyncSession = Depends(get_db)
):
    """Create a new paper collection."""
    collection = Collection(
        name=request.name,
        description=request.description,
        is_public=request.is_public,
    )
    db.add(collection)
    await db.flush()

    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        is_public=collection.is_public,
        paper_count=0,
        created_at=collection.created_at.isoformat(),
    )


@router.get("/", response_model=list[CollectionResponse])
async def list_collections(db: AsyncSession = Depends(get_db)):
    """List all collections with paper counts."""
    result = await db.execute(
        select(
            Collection,
            func.count(CollectionPaper.id).label("paper_count"),
        )
        .outerjoin(CollectionPaper, CollectionPaper.collection_id == Collection.id)
        .group_by(Collection.id)
        .order_by(Collection.created_at.desc())
    )

    return [
        CollectionResponse(
            id=row[0].id,
            name=row[0].name,
            description=row[0].description,
            is_public=row[0].is_public,
            paper_count=row[1],
            created_at=row[0].created_at.isoformat(),
        )
        for row in result.fetchall()
    ]


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
async def get_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a collection with all its papers."""
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Fetch papers in collection
    result = await db.execute(
        select(Paper, CollectionPaper.user_notes, CollectionPaper.added_at)
        .join(CollectionPaper, CollectionPaper.paper_id == Paper.id)
        .where(CollectionPaper.collection_id == collection_id)
        .order_by(CollectionPaper.added_at.desc())
    )

    papers = [
        {
            "id": row[0].id,
            "title": row[0].title,
            "abstract": row[0].abstract,
            "year": row[0].year,
            "citation_count": row[0].citation_count,
            "url": row[0].url,
            "user_notes": row[1],
            "added_at": row[2].isoformat() if row[2] else None,
        }
        for row in result.fetchall()
    ]

    paper_count = len(papers)

    return CollectionDetailResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        is_public=collection.is_public,
        paper_count=paper_count,
        created_at=collection.created_at.isoformat(),
        papers=papers,
    )


@router.post("/{collection_id}/papers", status_code=201)
async def add_paper_to_collection(
    collection_id: int,
    request: AddPaperRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a paper to a collection with optional notes."""
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper = await db.get(Paper, request.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Check if already in collection
    existing = await db.execute(
        select(CollectionPaper).where(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == request.paper_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Paper already in collection")

    entry = CollectionPaper(
        collection_id=collection_id,
        paper_id=request.paper_id,
        user_notes=request.user_notes,
    )
    db.add(entry)

    return {"message": "Paper added to collection", "paper_id": request.paper_id}


@router.delete("/{collection_id}/papers/{paper_id}", status_code=204)
async def remove_paper_from_collection(
    collection_id: int, paper_id: int, db: AsyncSession = Depends(get_db)
):
    """Remove a paper from a collection."""
    result = await db.execute(
        select(CollectionPaper).where(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Paper not in collection")

    await db.delete(entry)


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an entire collection."""
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    await db.delete(collection)
