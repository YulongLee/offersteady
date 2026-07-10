from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class RetrievalBoundaryStatus:
    retrieval_port: str
    pgvector_schema: str
    extension_name: str


def describe_retrieval_boundary(settings: Settings) -> RetrievalBoundaryStatus:
    return RetrievalBoundaryStatus(
        retrieval_port="knowledge-retrieval-service",
        pgvector_schema=settings.pgvector_schema,
        extension_name=settings.pgvector_extension_name,
    )
