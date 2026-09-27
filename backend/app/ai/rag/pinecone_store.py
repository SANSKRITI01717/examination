"""
Pinecone vector store, called via its plain HTTPS REST API rather than the
`pinecone` SDK — same "direct HTTP call, no new dependency" pattern used for
the LLM and embedding clients.

⚠️ IMPORTANT — NOT VERIFIED AGAINST A LIVE PINECONE INSTANCE.
This was written with no internet access, so the exact current header names,
API version string, and control-plane response shape could not be checked
against Pinecone's live documentation. The request shapes below match
Pinecone's documented serverless REST API as of this codebase's training
data. Before relying on real retrieval:
  1. Verify against https://docs.pinecone.io/reference/api/introduction
  2. Confirm the `X-Pinecone-API-Version` header value is current
  3. Confirm the control-plane `describe_index` response still has a `host` field
Every method here raises RagError on any failure (auth, network, unexpected
response shape), and callers are required to treat that as "retrieval
unavailable" and fall back to standard mode — never let a wrong field name
here crash or block an evaluation (ai-pipeline.md §6 step 4). This is a
deliberate fail-safe design given the integration could not be tested live.
"""
from typing import Any, Dict, List, Optional

import httpx

from app.ai.rag.base import RagError, RetrievedChunk, VectorRecord, VectorStore
from app.core.config import settings

_CONTROL_PLANE_URL = "https://api.pinecone.io"
_API_VERSION = "2025-01"
_TIMEOUT_SECONDS = 20.0


class PineconeStore(VectorStore):
    def __init__(self) -> None:
        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX
        self._host: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Api-Key": self.api_key,
            "X-Pinecone-API-Version": _API_VERSION,
            "Content-Type": "application/json",
        }

    def _resolve_host(self) -> str:
        if not self.api_key:
            raise RagError("PINECONE_API_KEY is not configured")
        if self._host:
            return self._host

        try:
            response = httpx.get(
                f"{_CONTROL_PLANE_URL}/indexes/{self.index_name}",
                headers=self._headers(),
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise RagError(f"Pinecone control-plane request failed: {exc}") from exc

        if response.status_code != 200:
            raise RagError(
                f"Pinecone describe_index returned {response.status_code}: {response.text[:300]}"
            )

        try:
            host = response.json()["host"]
        except (ValueError, KeyError, TypeError) as exc:
            raise RagError(f"Could not parse Pinecone describe_index response: {exc}") from exc

        self._host = f"https://{host}"
        return self._host

    def upsert(self, namespace: str, records: List[VectorRecord]) -> None:
        if not records:
            return
        host = self._resolve_host()
        body = {
            "namespace": namespace,
            "vectors": [
                {"id": r.vector_id, "values": r.values, "metadata": r.metadata}
                for r in records
            ],
        }
        try:
            response = httpx.post(
                f"{host}/vectors/upsert", headers=self._headers(), json=body, timeout=_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            raise RagError(f"Pinecone upsert failed: {exc}") from exc
        if response.status_code != 200:
            raise RagError(f"Pinecone upsert returned {response.status_code}: {response.text[:300]}")

    def query(
        self,
        namespace: str,
        vector: List[float],
        top_k: int,
        question_id_filter: Optional[List[int]] = None,
    ) -> List[RetrievedChunk]:
        host = self._resolve_host()
        body: Dict[str, Any] = {
            "namespace": namespace,
            "vector": vector,
            "topK": top_k,
            "includeMetadata": True,
        }
        if question_id_filter is not None:
            body["filter"] = {"question_id": {"$in": question_id_filter}}

        try:
            response = httpx.post(
                f"{host}/query", headers=self._headers(), json=body, timeout=_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            raise RagError(f"Pinecone query failed: {exc}") from exc
        if response.status_code != 200:
            raise RagError(f"Pinecone query returned {response.status_code}: {response.text[:300]}")

        try:
            matches = response.json().get("matches", [])
        except ValueError as exc:
            raise RagError(f"Could not parse Pinecone query response: {exc}") from exc

        chunks = []
        for m in matches:
            meta = m.get("metadata", {}) or {}
            vector_id = m.get("id", "")
            doc_id_str, _, chunk_index_str = vector_id.partition(":")
            chunks.append(
                RetrievedChunk(
                    doc_id=int(meta.get("doc_id", doc_id_str or 0)),
                    chunk_index=int(meta.get("chunk_index", chunk_index_str or 0)),
                    score=float(m.get("score", 0.0)),
                    text=meta.get("text", ""),
                    title=meta.get("title", ""),
                )
            )
        return chunks

    def delete_by_doc(self, namespace: str, doc_id: int) -> None:
        host = self._resolve_host()
        try:
            response = httpx.post(
                f"{host}/vectors/delete",
                headers=self._headers(),
                json={"namespace": namespace, "filter": {"doc_id": {"$eq": doc_id}}},
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise RagError(f"Pinecone delete failed: {exc}") from exc
        if response.status_code != 200:
            raise RagError(f"Pinecone delete returned {response.status_code}: {response.text[:300]}")
