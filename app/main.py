from fastapi import FastAPI

# FastAPI 객체 생성
app = FastAPI()

# Health check API
@app.get("/health")
def health_check():
    return {"status": "ok"}
