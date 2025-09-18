import asyncio
import json
import logging
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    # Connect to the Go MCP tool (service name resolves via Docker Compose)
    async with stdio_client("news_tool", 8765) as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)

        tools = await session.list_tools()
        logging.info("Available tools:", tools)

        result = await session.call_tool(
            tool_name="news_fetcher",
            arguments={"sources": ["hn", "reddit"]}
        )

        logging.info("\nFetched results from Go tool:")
        logging.info(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())