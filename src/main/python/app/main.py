
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/timestamp")
def get_timestamp():
    """Returns the current timestamp."""
    return {"timestamp": datetime.now().isoformat()}