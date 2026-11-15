from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_health, routes_query, routes_retrieval, routes_upload
from app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NyayAI",
    description=(
        "Retrieval-augmented legal information assistant for Indian citizens. "
        "Answers are generated only from indexed official Acts and every answer "
        "carries its source sections. POST /api/retrieve returns the retrieved "
        "chunks alone, without generation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router, prefix="/api", tags=["health"])
app.include_router(routes_query.router, prefix="/api", tags=["query"])
app.include_router(routes_retrieval.router, prefix="/api", tags=["retrieval"])
app.include_router(routes_upload.router, prefix="/api", tags=["upload"])


@app.get("/")
def root():
    return {"name": "NyayAI", "docs": "/docs"}
