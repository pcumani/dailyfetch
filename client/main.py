import uvicorn
from fastapi import FastAPI
from api.endpoints import agent_router


app = FastAPI()

app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80)