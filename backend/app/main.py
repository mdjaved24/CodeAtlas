from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="CodeAtlas API",
    description="Codebase intelligence platform API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to CodeAtlas API",
        "version": "0.1.0",
    }



@app.get("/health")
def health_check():
    return {
        "status":"ok",
        "service": "codeatlas-api",
    }



if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
        )