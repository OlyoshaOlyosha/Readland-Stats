"""Thin launcher. Keeps `python main.py` working after restructure."""

import uvicorn

from app.config import DEBUG, HOST, PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
