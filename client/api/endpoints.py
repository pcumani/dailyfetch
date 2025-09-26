import logging
import requests
from typing import Annotated, Union, List, Literal, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from agent.agent import MCPClient

server_url = "http://news_tools:8000/mcp"
agent_router = APIRouter()
client = MCPClient(server_url=server_url)


class AgentTool(BaseModel):
    name: str
    description: str
    input_schema: dict | None = None

class ListToolsResponse(BaseModel):
    model: str
    tools: List[AgentTool]

class ModelConfig(BaseModel):
    model: Literal["GOOGLE", "OPENAI"] = Field(
        default="GOOGLE",
        title="Inference provider",
        description="Inference provider for the LLM model to be used. Can be one of GOOGLE or OPENAI"
    )
    api_key: Optional[str] = Field(
        default=None,
        title="API key",
        description="API key to be used to access the model"
    )

@agent_router.get("/health")
async def healthcheck() -> str:
    try:
        response = requests.get(server_url.replace('mcp', 'health'), timeout=2)
        if response.status_code == 200:
            return "OK"
    except Exception as e:
        raise HTTPException(status_code={500}, 
                            detail=f"Error pinging the server: {e}")

    raise HTTPException(status_code={response.status_code}, 
                            detail=f"Server responded with status: {response.status_code} {response.content}")

@agent_router.post("/set_model", status_code=201)
async def start_client(config: ModelConfig):
        global client
        client.init_model(model=config.model, api_key=config.api_key)

@agent_router.get("/list_model_tools")
async def list_tools() -> ListToolsResponse:
    global client
    if client.model is None:
        try:
            client.init_model(model='GOOGLE')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error instantiating the model, please use the set_model endpoint: {e}")

    try:
        tools = await client.list_tools()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error starting the client or connecting to server: {e}")

    
    return ListToolsResponse(model=client.model.model, tools=tools)


@agent_router.post("/summarize_news",  status_code=200)
async def start_client(news_categories: Annotated[Union[List[str], str, None], Query(title="Categories of news to be searched",
            description="Only news of these categories will be searched. A list of categories can be passed. Can be left blank to look for general news. "+
                                "Possible values: 'technology', 'business', 'entertainment', 'science', 'sport', 'general'")] = 'general',
            news_sources: Annotated[Union[List[str], str, None], Query(title="News sources",
            description="The sources where to find the news. One of 'googlenews', 'guardian', 'reddit'")] = 'googlenews', 
            )-> str:
    global client
    if client.model is None:
        try:
            client.init_model(model='GOOGLE')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error instantiating the model, please use the set_model endpoint: {e}")

    try:
        result = await client.process_query(news_categories=news_categories, news_sources=news_sources)
    except Exception as e:
        raise HTTPException(status_code=400, 
                            detail=f"Error during processing query: {e}")
    if result.startswith('ERROR'):
        raise HTTPException(status_code=400, 
                            detail=f"Error during news fetching: {result}")
    return result
    

