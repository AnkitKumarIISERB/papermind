"""SQLAlchemy models for PaperMind."""

import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.core.config import get_settings

settings = get_settings()


class Paper(Base):
    """Academic paper metadata."""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    semantic_scholar_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    year = Column(Integer, nullable=True, index=True)
    venue = Column(String(512), nullable=True)
    citation_count = Column(Integer, default=0)
    reference_count = Column(Integer, default=0)
    influential_citation_count = Column(Integer, default=0)
    url = Column(String(1024), nullable=True)
    is_open_access = Column(Boolean, default=False)
    fields_of_study = Column(Text, nullable=True)  # JSON-encoded list
    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )

    # Relationships
    authors = relationship(
        "PaperAuthor", back_populates="paper", cascade="all, delete-orphan"
    )
    embedding = relationship(
        "PaperEmbedding",
        back_populates="paper",
        uselist=False,
        cascade="all, delete-orphan",
    )
    collection_entries = relationship(
        "CollectionPaper", back_populates="paper", cascade="all, delete-orphan"
    )


class Author(Base):
    """Author metadata."""

    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    semantic_scholar_id = Column(String(64), unique=True, nullable=True, index=True)
    name = Column(String(512), nullable=False)

    papers = relationship("PaperAuthor", back_populates="author")


class PaperAuthor(Base):
    """Many-to-many relationship between papers and authors with position."""

    __tablename__ = "paper_authors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, default=0)  # Author ordering

    paper = relationship("Paper", back_populates="authors")
    author = relationship("Author", back_populates="papers")

    __table_args__ = (
        UniqueConstraint("paper_id", "author_id", name="uq_paper_author"),
    )


class Citation(Base):
    """Directed citation edge: citing_paper → cited_paper."""

    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    citing_paper_id = Column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cited_paper_id = Column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "citing_paper_id", "cited_paper_id", name="uq_citation_edge"
        ),
    )


class PaperEmbedding(Base):
    """pgvector embedding for a paper's abstract."""

    __tablename__ = "paper_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(
        Integer,
        ForeignKey("papers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    embedding = Column(Vector(settings.embedding_dimension), nullable=False)

    paper = relationship("Paper", back_populates="embedding")


class Collection(Base):
    """User-created paper collection."""

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )

    papers = relationship(
        "CollectionPaper", back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionPaper(Base):
    """Paper added to a collection with optional user notes."""

    __tablename__ = "collection_papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    paper_id = Column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    user_notes = Column(Text, nullable=True)
    added_at = Column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )

    collection = relationship("Collection", back_populates="papers")
    paper = relationship("Paper", back_populates="collection_entries")

    __table_args__ = (
        UniqueConstraint(
            "collection_id", "paper_id", name="uq_collection_paper"
        ),
    )


class QueryHistory(Base):
    """Log of user searches and Q&A queries."""

    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(32), nullable=False)  # "search" | "qa" | "review"
    results_count = Column(Integer, default=0)
    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )


class TopicSearch(Base):
    """Record of topic-based paper ingestion jobs."""

    __tablename__ = "topic_searches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(512), nullable=False)
    status = Column(String(32), default="pending")  # pending | running | done | failed
    papers_found = Column(Integer, default=0)
    papers_embedded = Column(Integer, default=0)
    celery_task_id = Column(String(256), nullable=True)
    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )
    completed_at = Column(DateTime, nullable=True)
