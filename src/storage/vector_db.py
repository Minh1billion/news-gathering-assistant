from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

QDRANT_COLLECTION = "articles"


class QdrantStore:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client

    def ensure_collection(self, vector_size: int) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if QDRANT_COLLECTION not in existing:
            self.client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert_articles(self, df, embeddings) -> int:
        points = [
            PointStruct(
                id=int(row["id"]),
                vector=embeddings[i].tolist(),
                payload={
                    "title": row["title"],
                    "source": row["source"],
                    "url": row["url"],
                    "published_at": str(row["published_at"]),
                    "tech_score": float(row["tech_score"]),
                    "tech_topic": row["tech_topic"],
                    "tokenized": row["tokenized"],
                    "content_snippet": row["content"][:300],
                },
            )
            for i, (_, row) in enumerate(df.iterrows())
        ]

        batch_size = 256
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points[i : i + batch_size],
            )

        return len(points)

    def scroll_all(self) -> tuple[list[dict], list[list[float]]]:
        payloads: list[dict] = []
        vectors: list[list[float]] = []
        offset = None

        while True:
            result, next_offset = self.client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            if not result:
                break
            for point in result:
                payloads.append(point.payload)
                vectors.append(point.vector)
            offset = next_offset
            if offset is None:
                break

        return payloads, vectors