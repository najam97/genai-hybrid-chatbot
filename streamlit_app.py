import json
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from core.config import Config
from core.router import QueryClassifier, QueryRoute
from main import create_llm_client, get_model_name
from pipelines.sql_pipeline import SQLPipeline
from pipelines.vector_pipeline import VectorPipeline

HISTORY_PATH = Path("data/streamlit_history.json")


def ensure_history_file() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text("[]", encoding="utf-8")


def load_history() -> list[dict]:
    ensure_history_file()
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_history(history: list[dict]) -> None:
    ensure_history_file()
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def add_history_entry(entry: dict) -> None:
    history = load_history()
    history.insert(0, entry)
    save_history(history)
    st.session_state.history = history


def delete_history_entry(index: int) -> None:
    history = load_history()
    if 0 <= index < len(history):
        history.pop(index)
        save_history(history)
        st.session_state.history = history


def clear_history() -> None:
    save_history([])
    st.session_state.history = []


def init_app_state() -> None:
    if "initialized" in st.session_state:
        return

    try:
        Config.validate()
    except Exception as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()

    client = create_llm_client()
    model_name = get_model_name()
    st.session_state.client = client
    st.session_state.model_name = model_name
    st.session_state.classifier = QueryClassifier(client=client, model=model_name)
    st.session_state.sql_pipeline = SQLPipeline(db_path=Config.DB_PATH, client=client, model=model_name)
    st.session_state.vector_pipeline = VectorPipeline(client=client, model=model_name)
    st.session_state.history = load_history()
    st.session_state.current_query = ""
    st.session_state.current_response = ""
    st.session_state.current_background = []
    st.session_state.initialized = True


def render_background(items: list[dict]) -> None:
    if not items:
        st.info("No background details available.")
        return

    for item in items:
        with st.expander(item.get("type", "detail").capitalize(), expanded=False):
            if item["type"] == "routing":
                st.markdown(f"**Route:** {item['route'].upper()}  \n**Confidence:** {item['confidence']:.2f}  \n**Reasoning:** {item['reasoning']}")
            elif item["type"] == "sql_generated":
                st.code(item["sql"], language="sql")
            elif item["type"] == "sql_raw_data":
                st.json(item["data"])
            elif item["type"] == "vector_retrieval":
                for doc in item.get("docs", []):
                    st.markdown(f"**{doc.get('title')}**  \n{doc.get('content')}")
            elif item["type"] in {"sql_error", "server_error"}:
                st.error(item["error"])
            else:
                st.write(item)


def query_chatbot(query: str) -> tuple[str, list[dict]]:
    classifier = st.session_state.classifier
    sql_pipeline = st.session_state.sql_pipeline
    vector_pipeline = st.session_state.vector_pipeline

    decision = classifier.classify(query)
    background = [
        {
            "type": "routing",
            "route": decision.route.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
        }
    ]

    if decision.route == QueryRoute.SQL:
        try:
            sql_query = sql_pipeline._generate_sql_query(query)
            background.append({"type": "sql_generated", "sql": sql_query})
        except Exception as exc:
            background.append({"type": "sql_error", "error": str(exc)})
            return f"SQL generation failed: {exc}", background

        try:
            raw_data = sql_pipeline.execute_read_only_query(sql_query)
            background.append({"type": "sql_raw_data", "data": raw_data})
        except Exception as exc:
            background.append({"type": "sql_error", "error": str(exc)})
            return f"SQL execution failed: {exc}", background

        answer = sql_pipeline._format_response(query, raw_data)
        return answer, background

    if decision.route == QueryRoute.VECTOR:
        docs = vector_pipeline._retrieve_documents(query, top_k=3)
        background.append({"type": "vector_retrieval", "docs": docs})
        if not docs:
            return (
                "I couldn't find relevant documents for that query.",
                background,
            )

        context = "\n\n".join([f"[Source: {doc['title']}]\n{doc['content']}" for doc in docs])
        answer = vector_pipeline._generate_response(query, context)
        return answer, background

    return (
        "I'm sorry, I couldn't determine how to process your request.",
        background,
    )


def load_history_item(index: int) -> None:
    history = st.session_state.history
    if 0 <= index < len(history):
        item = history[index]
        st.session_state.current_query = item.get("query", "")
        st.session_state.current_response = item.get("response", "")
        st.session_state.current_background = item.get("background", [])


def main() -> None:
    st.set_page_config(page_title="Hybrid Chatbot", layout="wide")
    st.title("Hybrid Chatbot UI")
    st.write("A Streamlit frontend for the hybrid SQL + vector chatbot. The old FastAPI frontend is preserved as backup in `api/app.py`.")

    init_app_state()

    query_col, response_col, background_col = st.columns([3, 4, 3])

    with query_col:
        tab_chat, tab_history = st.tabs(["Chat", "History"])

        with tab_chat:
            st.session_state.current_query = st.text_area(
                "Ask a question:",
                value=st.session_state.current_query,
                key="query_input",
                height=180,
            )
            buttons = st.columns([1, 1, 1])
            with buttons[0]:
                submit = st.button("Send", type="primary")
            with buttons[1]:
                clear_current = st.button("Clear Current")
            with buttons[2]:
                refresh_history = st.button("Reload History")

            if clear_current:
                st.session_state.current_query = ""
                st.session_state.current_response = ""
                st.session_state.current_background = []

            if refresh_history:
                st.session_state.history = load_history()

            if submit:
                with st.spinner("Processing your query..."):
                    response, background = query_chatbot(st.session_state.current_query)
                    st.session_state.current_response = response
                    st.session_state.current_background = background
                    add_history_entry(
                        {
                            "query": st.session_state.current_query,
                            "response": response,
                            "background": background,
                            "ts": time.time(),
                        }
                    )

        with tab_history:
            st.markdown("### Saved Conversations")
            if not st.session_state.history:
                st.info("No saved conversations yet.")
            else:
                for index, item in enumerate(st.session_state.history):
                    with st.expander(f"{item.get('query', 'No query')}", expanded=False):
                        st.write(item.get("response", ""))
                        if st.button("Load into chat", key=f"load_{index}"):
                            load_history_item(index)
                        if st.button("Delete", key=f"delete_{index}"):
                            delete_history_entry(index)
            if st.button("Clear All History"):
                clear_history()

    with response_col:
        st.markdown("### Response")
        st.write(st.session_state.current_response or "No response yet.")

    with background_col:
        st.markdown("### Background")
        render_background(st.session_state.current_background)


if __name__ == "__main__":
    main()
