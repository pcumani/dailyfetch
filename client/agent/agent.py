import asyncio
import os
import logging
from typing import Optional, List, Union
from datetime import timedelta
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from dotenv import load_dotenv

from agent.models.google import GoogleModel
from agent.models.openai import OpenAIModel

logging.basicConfig(level=logging.INFO)

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, server_url: str = "http://news_tools:8000/mcp"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model = None
        self.server_url = server_url

    def init_model(self, model: str = 'GOOGLE', api_key: Optional[str]=None):
        if model.upper() == "GOOGLE":
            api_key = os.getenv("GOOGLE_API_KEY") if api_key is None else api_key
            self.model = GoogleModel(model="gemini-2.5-flash", api_key=api_key)
        else:
            api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
            OpenAIModel(model="gpt-4o-mini", api_key=api_key)
            
    async def list_tools(self):
        """List available tools from the MCP server."""

        async with streamablehttp_client(
            url=self.server_url,
            timeout=timedelta(seconds=10),
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()

                logging.info(f"\n Connected to MCP server at {self.server_url}")
                response = await self.session.list_tools()


        tool_list = []
        logging.info("Available tools:")
        for tool in response.tools:
            tool_list.append({'name': tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
            logging.info(f"Tool: {tool.name}, Description: {tool.description}, Input Schema: {tool.inputSchema}")
        
        return tool_list

    async def process_query(self, news_categories: Union[List[str], str, None]=['technology'], 
                            news_sources: Union[List[str], str, None]=['reddit']):
        """Process incoming query"""  

        async with streamablehttp_client(
            url=self.server_url,
            timeout=timedelta(seconds=10),
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()

                result = await self.session.call_tool(name="news_fetcher",
                    arguments={"sources": news_sources}
                    )

        
        result = eval(result.content[0].text.replace('null', 'None'))['results']
        logging.info(f"Fetched {len(result)} results from Go tool: {str(result)[:100] + '...' if len(str(result)) > 100 else str(result)}")
        result = [x for x in result if 'data' in x and x['data'] is not None]

        if len(result) == 0:
            logging.warning("No valid news results to summarize.")
            return "No valid news results to summarize."
        elif len([x for x in result if not (isinstance(x['data'], str) and x['data'].startswith('Error'))]) == 0:
            errors = [x for x in result if isinstance(x['data'], str) and x['data'].startswith('Error')]
            logging.error(f"Error in news results: {errors}")
            return f"ERROR in news results: {errors}"

        try:
            summary = await self.model.summarize(text=str(result))
            return summary
        except TypeError as e:
            logging.error(f"ERROR during summarization: {e}")
            raise

async def main():
    import os
    import requests
    
    logging.info('Check server reachable')
    health = requests.get("http://news_tools:8000/health")
    if health.status_code != 200:
        logging.error("Server unreachable")
        raise

    server_port = os.getenv("MCP_SERVER_PORT", 8000)

    server_url = f"http://news_tools:{server_port}/mcp"

    client = MCPClient(server_url=server_url)
    client.init_model('GOOGLE')
    logging.info("Starting MCP Client...")
    
    await client.process_query()
    

if __name__ == "__main__":

    asyncio.run(main())