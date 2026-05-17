from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Ensure environment variables already loaded by main/test_config
from core.config import Config
from main import create_llm_client, get_model_name
from core.router import QueryClassifier, QueryRoute
from pipelines.sql_pipeline import SQLPipeline
from pipelines.vector_pipeline import VectorPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="Hybrid Chatbot Web UI")

# Static files
app.mount("/static", StaticFiles(directory="./static"), name="static")

# Jinja2 environment (explicit, avoids TemplateResponse/Jinja2Templates cache issues)
templates_env = Environment(
    loader=FileSystemLoader("./templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


class ChatRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    template = templates_env.get_template("index.html")
    rendered = template.render()
    return HTMLResponse(rendered)


@app.on_event("startup")
async def validate_config():
    """Validate configuration on startup so missing settings fail early."""
    Config.validate()


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    user_query = req.query.strip()
    background = []

    try:
        # Initialize LLM client and pipelines
        client = create_llm_client()
        model_name = get_model_name()

        classifier = QueryClassifier(client=client, model=model_name)
        sql_pipeline = SQLPipeline(db_path=Config.DB_PATH, client=client, model=model_name)
        vector_pipeline = VectorPipeline(client=client, model=model_name)

        # 1) Classify
        decision = classifier.classify(user_query)
        background.append({"type": "routing", "route": decision.route.value, "confidence": decision.confidence, "reasoning": decision.reasoning})

        # 2) Dispatch
        if decision.route == QueryRoute.SQL:
            # Generate SQL (but do not rely on pipeline.run which hides intermediate)
            try:
                sql = sql_pipeline._generate_sql_query(user_query)
            except Exception as e:
                return JSONResponse({"response": f"SQL generation failed: {e}", "background": background})

            background.append({"type": "sql_generated", "sql": sql})

            try:
                raw_data = sql_pipeline.execute_read_only_query(sql)
                background.append({"type": "sql_raw_data", "data": raw_data})
            except Exception as e:
                background.append({"type": "sql_error", "error": str(e)})
                return JSONResponse({"response": f"Error executing SQL: {e}", "background": background})

            # Format final answer
            final_answer = sql_pipeline._format_response(user_query, raw_data)
            return JSONResponse({"response": final_answer, "background": background})

        elif decision.route == QueryRoute.VECTOR:
            # Retrieve docs
            docs = vector_pipeline._retrieve_documents(user_query, top_k=3)
            background.append({"type": "vector_retrieval", "docs": docs})

            # Generate final answer
            final_answer = vector_pipeline._generate_response(user_query, "\n\n".join([f"[Source: {d['title']}]\n{d['content']}" for d in docs]))
            return JSONResponse({"response": final_answer, "background": background})

        else:
            return JSONResponse({"response": "I'm sorry, I couldn't determine how to process your request. Please try rephrasing.", "background": background})

    except Exception as e:
        logger.exception("Chat endpoint failure")
        background.append({"type": "server_error", "error": str(e)})
        return JSONResponse({"response": f"Error: {e}", "background": background})
