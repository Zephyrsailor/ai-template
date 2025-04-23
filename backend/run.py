import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Use reload=True for development
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)