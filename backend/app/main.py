from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat_router

# --- FastAPI App ---
app = FastAPI(title="AI Template API")

# --- CORS Middleware ---
# Adjust origins as needed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for simplicity, restrict in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Include Routers ---
app.include_router(chat_router)

# --- Basic Root Endpoint ---
@app.get("/")
async def root():
    return {"message": "AI Template Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)