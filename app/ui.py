from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.agent_graph import build_agent_graph
from app.config import settings
from app.retrieval import Retriever


st.set_page_config(page_title="EU AI Act Compliance Copilot", page_icon="⚖️", layout="wide")


@st.cache_resource
def load_runtime():
    retriever = Retriever()
    graph = build_agent_graph(retriever)
    return graph, retriever


graph, retriever = load_runtime()

st.title("EU AI Act Compliance Copilot")
st.caption("Agentic RAG prototype - preliminary compliance research, not legal advice.")

with st.sidebar:
    st.subheader("Runtime")
    st.write(f"LLM: `{settings.llm_model}`")
    st.write(f"Embeddings: `{settings.embedding_model}`")
    st.write(f"Collection: `{settings.qdrant_collection}`")
    st.write(f"As-of date: `{date.today().isoformat()}`")
    if retriever.ready():
        st.success("Vector index ready")
    else:
        st.error("Vector index missing")
        st.code("python scripts/ingest.py", language="powershell")
        st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("trace"):
            with st.expander("Agent execution"):
                st.dataframe(message["trace"], use_container_width=True)
        if message.get("evidence"):
            with st.expander("Retrieved evidence"):
                for item in message["evidence"]:
                    st.markdown(
                        f"**[{item['citation_id']}] {item['title']}**  \n"
                        f"Page: {item.get('page')} | Section: {item.get('section') or '-'} | "
                        f"Score: {item.get('score', 0):.3f}"
                    )
                    st.caption(item["text"][:700] + ("..." if len(item["text"]) > 700 else ""))

question = st.chat_input("Ask an EU AI Act question...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Running agent workflow..."):
            result = graph.invoke(
                {
                    "question": question,
                    "as_of": date.today().isoformat(),
                    "retry_count": 0,
                    "trace": [],
                }
            )
        st.markdown(result["final_answer"])
        with st.expander("Agent execution"):
            st.dataframe(result.get("trace", []), use_container_width=True)
        with st.expander("Retrieved evidence"):
            for item in result.get("evidence", []):
                st.markdown(
                    f"**[{item['citation_id']}] {item['title']}**  \n"
                    f"Page: {item.get('page')} | Section: {item.get('section') or '-'} | "
                    f"Score: {item.get('score', 0):.3f}"
                )
                st.caption(item["text"][:700] + ("..." if len(item["text"]) > 700 else ""))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["final_answer"],
            "trace": result.get("trace", []),
            "evidence": result.get("evidence", []),
        }
    )
