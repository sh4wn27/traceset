from fastapi import FastAPI

from backend.routers import commits, papers, patents, traces

app = FastAPI(
    title="Traceset API",
    description="Competitive intelligence: link commits, papers, and patents into traces.",
    version="0.1.0",
)

app.include_router(commits.router)
app.include_router(papers.router)
app.include_router(patents.router)
app.include_router(traces.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
