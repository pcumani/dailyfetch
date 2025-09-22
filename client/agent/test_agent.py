import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import types

sys.modules['mcp'] = types.ModuleType('mcp')
sys.modules['mcp.client.streamable_http'] = types.ModuleType('streamable_http')
sys.modules['agent.models.google'] = types.ModuleType('google')
sys.modules['agent.models.openai'] = types.ModuleType('openai')

from agent.agent import MCPClient

class DummyGoogleModel:
    def __init__(self, model, api_key):
        self.model = model
        self.api_key = api_key
    async def summarize(self, text):
        return "summary"

class DummySession:
    async def initialize(self):
        pass
    async def list_tools(self):
        class Tool:
            name = "news_fetcher"
            description = "Fetches news"
            inputSchema = {"sources": ["reddit"]}
        class Response:
            tools = [Tool()]
        return Response()
    async def call_tool(self, name, arguments):
        class Content:
            text = "{'results': [{'data': 'Some news'}]}"
        class Result:
            content = [Content()]
        return Result()

class TestMCPClient(unittest.IsolatedAsyncioTestCase):
    @patch('agent.agent.GoogleModel', DummyGoogleModel)
    @patch('agent.agent.streamablehttp_client', AsyncMock())
    @patch('agent.agent.ClientSession', MagicMock())
    async def test_init_model_google(self):
        client = MCPClient()
        client.init_model('GOOGLE', api_key='dummy')
        self.assertIsInstance(client.model, DummyGoogleModel)
        self.assertEqual(client.model.model, "gemini-2.5-flash")

    @patch('agent.agent.GoogleModel', DummyGoogleModel)
    @patch('agent.agent.streamablehttp_client')
    @patch('agent.agent.ClientSession')
    async def test_list_tools(self, mock_session, mock_streamable):
        mock_streamable.return_value.__aenter__.return_value = (None, None, None)
        mock_session.return_value.__aenter__.return_value = DummySession()
        client = MCPClient()
        tools = await client.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]['name'], "news_fetcher")

    @patch('agent.agent.GoogleModel', DummyGoogleModel)
    @patch('agent.agent.streamablehttp_client')
    @patch('agent.agent.ClientSession')
    async def test_process_query(self, mock_session, mock_streamable):
        mock_streamable.return_value.__aenter__.return_value = (None, None, None)
        mock_session.return_value.__aenter__.return_value = DummySession()
        client = MCPClient()
        client.init_model('GOOGLE', api_key='dummy')
        summary = await client.process_query()
        self.assertEqual(summary, "summary")

if __name__ == "__main__":
    unittest.main()
