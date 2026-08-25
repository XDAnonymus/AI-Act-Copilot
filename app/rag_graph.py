from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.retrieval import Retriever
from app.schemas import RAGState


def build_rag_graph(retriever: Retriever):
    def prepare_query(state: RAGState) -> dict:
        query = state["query"].strip()
        if "ai act" not in query.lower() and "artificial intelligence act" not in query.lower():
            query = f"EU AI Act {query}"
        return {"query": query, "top_k": state.get("top_k", settings.retrieval_top_k)}

    def retrieve(state: RAGState) -> dict:
        return {"hits": retriever.search(state["query"], state.get("top_k"))}

    def select(state: RAGState) -> dict:
        seen: set[str] = set()
        selected: list[dict] = []
        for hit in state.get("hits", []):
            chunk_id = hit.get("chunk_id")
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            selected.append(hit)
            if len(selected) >= 6:
                break
        return {"hits": selected}

    def package(state: RAGState) -> dict:
        evidence = []
        for hit in state.get("hits", []):
            evidence.append(
                {
                    "chunk_id": hit["chunk_id"],
                    "source_id": hit["source_id"],
                    "title": hit["title"],
                    "url": hit["url"],
                    "page": hit.get("page"),
                    "section": hit.get("section"),
                    "text": hit["text"],
                    "score": hit.get("score", 0.0),
                }
            )
        return {"evidence": evidence}

    builder = StateGraph(RAGState)
    builder.add_node("prepare_query", prepare_query)
    builder.add_node("retrieve", retrieve)
    builder.add_node("select", select)
    builder.add_node("package", package)

    builder.add_edge(START, "prepare_query")
    builder.add_edge("prepare_query", "retrieve")
    builder.add_edge("retrieve", "select")
    builder.add_edge("select", "package")
    builder.add_edge("package", END)
    return builder.compile()
