import asyncio
import logging
import json
from typing import Optional
from datetime import timedelta
from contextlib import AsyncExitStack

from mcp import ClientSession
#from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from dotenv import load_dotenv

from src.models.google import GoogleModel

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, server_url: str = "http://news_tools:8000/mcp"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model = GoogleModel()
        self.server_url = server_url
    
    async def connect_to_server(self):
        """Connect to an MCP server via HTTP
        """
        logging.info(f"Connecting to server: {self.server_url}")
        async with streamablehttp_client(
                    url=self.server_url,
                    timeout=timedelta(seconds=60),
                ) as (read_stream, write_stream, get_session_id):
                    await self._run_session(read_stream, write_stream, get_session_id)

    async def _run_session(self, read_stream, write_stream, get_session_id):
        """Run the MCP session with the given streams."""
        logging.info("Initializing MCP session...")
        async with ClientSession(read_stream, write_stream) as session:
            self.session = session
            await session.initialize()

            logging.info(f"\n Connected to MCP server at {self.server_url}")
            if get_session_id:
                session_id = get_session_id()
                if session_id:
                    logging.info(f"Session ID: {session_id}")

            # Run interactive loop
            await self.process_query()

    async def process_query(self):
        """Run an interactive chat loop"""

        response = await self.session.list_tools()
        logging.info("Available tools:")
        for tool in response.tools:
            logging.info(f"Tool: {tool.name}, Description: {tool.description}, Input Schema: {tool.inputSchema}")        

        result = await self.session.call_tool(
            name="news_fetcher",
            arguments={"sources": [ "reddit"]}
        )

        result = eval(result.content[0].text.replace('null', 'None'))['results']
        logging.info(f"Fetched {len(result)} results from Go tool: {str(result)[:100] + '...' if len(str(result)) > 100 else str(result)}")
        result = [x for x in result if 'data' in x and x['data'] is not None]

        if len(result) == 0:
            logging.warning("No valid news results to summarize.")
            return "No valid news results to summarize."
        elif len([x for x in result if not x['data'].startswith('Error:')]) ==0:
            logging.error(f"Error in news results: {[x for x in result if x['data'].startswith('Error:')]}")
            return f"Error in news results: {[x for x in result if x['data'].startswith('Error:')]}"

        try:
            summary = await self.model.summarize(text=str(result))
            logging.info(f"====== Summary: {summary}")
            return summary
        except TypeError as e:
            logging.error(f"Error during summarization: {e}")
            return "Error during summarization."

async def main():
    import os
    # Default server URL - can be overridden with environment variable
    # Most MCP streamable HTTP servers use /mcp as the endpoint
    server_port = os.getenv("MCP_SERVER_PORT", 8000)
    logging.basicConfig(level=logging.INFO)
    server_url = f"http://news_tools:{server_port}/mcp"

    client = MCPClient(server_url=server_url)
    logging.info("Starting MCP Client...")

    await client.connect_to_server()
    

if __name__ == "__main__":
    import sys
    asyncio.run(main())