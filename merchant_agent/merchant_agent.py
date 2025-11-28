"""
Main MerchantAgent class - facade for easy merchant integration
"""

import asyncio
import logging
import time
import os
import json
from typing import Optional
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import internal modules
from .config import MerchantAgentConfig
from .tools import MerchantTools, set_merchant_tools, get_merchant_tools
from .agent.llm_agent import create_merchant_agent
from .session import set_session_id, get_session_id

logger = logging.getLogger(__name__)

class MerchantAgent:
    def __init__(
        self,
        config: MerchantAgentConfig,
        merchant_tools: MerchantTools,
    ):
        """
        Initialize the Merchant Agent.
        
        Args:
            config: MerchantAgentConfig with API key, model, app name, etc.
            merchant_tools: Your MerchantTools implementation with get_products and process_new_order
        """
        # Validate config
        config.validate()
        
        self.config = config
        self.merchant_tools = merchant_tools
        self.session_id: Optional[str] = None
        self.runner: Optional[Runner] = None
        self.session_service: Optional[InMemorySessionService] = None
        self.model = config.model

        # Set API key in environment for ADK/GenAI usage
        os.environ["GOOGLE_API_KEY"] = self.config.api_key
        
        # Set up logging
        self._setup_logging()
        
        # Set the merchant tools globally so they're available to the agent
        set_merchant_tools(merchant_tools)
        
        logger.info(f"MerchantAgent initialized with config: {config.app_name}")
    
    def _setup_logging(self) -> None:
        """Configure logging based on config settings"""
        log_level = getattr(logging, self.config.log_level, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        if self.config.enable_debug:
            logging.getLogger().setLevel(logging.DEBUG)
    
    async def initialize(self) -> None:
        """
        Initialize the agent's session and runner.
        Must be called before running the agent.
        """
        # Generate session ID if not provided
        if not self.config.session_id:
            self.config.session_id = f"{self.config.user_id}_{int(time.time())}"
        
        self.session_id = self.config.session_id
        set_session_id(self.session_id)
        
        # Create session service
        self.session_service = InMemorySessionService()
        await self.session_service.create_session(
            app_name=self.config.app_name,
            user_id=self.config.user_id,
            session_id=self.session_id
        )
        
        # Create runner
        self.runner = Runner(
            agent=create_merchant_agent(self.model, self.config.app_name),
            app_name=self.config.app_name,
            session_service=self.session_service
        )
        
        logger.info(f"Agent initialized. Session: {self.session_id}")
    
    async def query_stream(self, user_input: str):
        if not self.runner:
            await self.initialize()

        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )

        async for event in self.runner.run_async(
            user_id=self.config.user_id,
            session_id=self.session_id,
            new_message=content
        ):
            # Tool call initiation
            if hasattr(event, "get_function_calls"):
                function_calls = event.get_function_calls()
                if function_calls:
                    for call in function_calls:
                        logger.info(f"Tool call initiated: {call.name}")
                        yield {
                            "type": "tool_call",
                            "is_final": False,
                            "content": {
                                "tool_name": call.name,
                                "parameters": getattr(call, "args", {}),
                                "call_id": getattr(call, "call_id", None)
                            }
                        }
                    continue

            # Tool call chunk
            if hasattr(event, "get_function_responses"):
                function_responses = event.get_function_responses()
                if function_responses:
                    for response in function_responses:
                        if response.name in ["search_products", "create_order", "view_cart"]:
                            logger.info(f"Streaming tool response for {response.name}")

                            tool_output = getattr(response, "response", None)

                            if isinstance(tool_output, str):
                                try:
                                    tool_output = json.loads(tool_output)
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse tool response string: {tool_output}")

                            if isinstance(tool_output, dict) and isinstance(tool_output.get("result"), str):
                                try:
                                    tool_output["result"] = json.loads(tool_output["result"])
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse 'result' field: {tool_output['result']}")

                            yield {
                                "type": "tool",
                                "is_final": False,
                                "content": tool_output
                            }
                        continue

            # llm response chunk
            if hasattr(event, "content") and event.content:
                part = event.content.parts[0]
                if getattr(part, "text", None):
                    yield {
                        "type": "chunk",
                        "is_final": event.is_final_response(),
                        "content": part.text
                    }

            # Stop when final
            if event.is_final_response():
                return
    
    def get_session_id(self) -> str:
        """Get the current session ID"""
        return self.session_id or "Not initialized"
    
    def get_config(self) -> MerchantAgentConfig:
        """Get the current configuration"""
        return self.config
