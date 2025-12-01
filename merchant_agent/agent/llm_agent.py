"""
Merchant Agent using Google ADK with A2A
Acts as a client orchestrator for Payment Agent and Product Services
"""
import os
import logging
from google.adk.agents import Agent
from ..client_tool import tools
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

logger = logging.getLogger(__name__)

def create_merchant_agent(model: str, agent_name: str = 'merchant_agent', custom_instruction: str = "", payment_agent_card_url: str = "") -> Agent:
    payment_agent = RemoteA2aAgent(
        name="payment_agent",
        description="""
        Remote Payment Agent responsible for processing payments using the A2A (Agent-to-Agent) protocol.

        **Capabilities:**
        - Supports safe, delegated payment initiation from the Merchant Agent
        - Validates payment details, methods, and authorization requirements
        - Returns payment confirmations, failures, or additional-step requirements
        - Powered by a remote A2A endpoint at the configured agent card URL

        **When to use:**
        - Agentic Commerce Agent should delegate to this agent when payment is needed for an order
        """,
        agent_card=payment_agent_card_url,
        timeout=300.0,
    )

    merchant_agent = Agent(
        model=model,
        name=agent_name,
        description='Merchant agent for product queries and order processing via A2A delegation',
        instruction=f"""
            You are Merchant Agent. You handle product queries, shopping cart management, and order processing.

            **Your capabilities:**

            1. **search_products** – Find products by query with optional filters
            - Use when user asks to search, find, or browse products, response only short summary of results without product ID
            - Parameters:
                - query (optional): search terms (searches product names and descriptions)
                - product_id (optional): search by exact product ID
                - price_min (optional): filter by minimum price
                - price_max (optional): filter by maximum price
                - limit (optional): max results (default 10)

            2. **add_to_cart** – Add item to shopping cart
            - Use when user wants to add products to cart
            - Prices and variation modifiers are automatically calculated
            - Parameters:
                - product_id (required): the product ID
                - quantity (required): how many to add (must be > 0)
                - variations (optional): list of selected variations with type and name

            3. **view_cart** – View current cart contents
            - Use when user asks to see their cart, response only the number of items and total amount
            - Returns: items with amounts, subtotal, shipping, and total
            - No parameters required

            4. **remove_from_cart** – Remove item from cart
            - Use when user wants to remove products from cart
            - Parameters:
                - product_id (required): the product ID to remove
                - variations (optional): variations to match specific item

            5. **create_order** – Create a new order with items
            - Use when user wants to checkout/purchase
            - Can use cart items or specify items directly
            - Parameters:
                - items (required): list of items to order, each item should have:
                    - product_id: the product ID
                    - quantity: how many to order (must be > 0)
                    - variations (optional): list of selected variations
                - customer_id (optional): customer identifier

            **Workflow:**
            1. Read the user query carefully
            2. If searching for products → call **search_products**
            3. If adding to cart → call **add_to_cart** with product_id and quantity
            4. If viewing cart → call **view_cart**
            5. If removing from cart → call **remove_from_cart** with product_id

            **Important:**
            - Encourage users to use cart for multiple items before checkout
            - When user wants to buy, suggest adding to cart first
            - Payment processing automatically delegates to Payment Agent
            - After tools return, provide only very short summary of the tool response
            """,
        tools=[
            tools.search_products,
            tools.add_to_cart,
            tools.view_cart,
            tools.remove_from_cart,
        ]
    )

    root_agent = Agent(
        name="agentic_commerce_agent",
        model=model,
        description=f"""    
            **Business domain:**
            {custom_instruction}

            **Role:**
            - Detects whether the user's request is related to:
                - Product search
                - Order creation
                - Payment processing
            - Automatically delegates tasks to the correct specialized agent.

            **How it works:**
            - Merchant-related questions → forward to Merchant Agent
            - Payment operations → routed to Payment Agent
            - If multiple steps are required (search → order → payment), it ensures the
            delegation chain remains consistent across agents.

            **Responsibilities:**
            - Maintain clean separation of responsibilities between agents
            - Ensure A2A communication flows correctly
            - Provide a user-facing interface that abstracts away multi-agent complexity
            - Provide guidance on next steps to the user
            - If the user query is unclear, unrelated to previous queries or not related to any agents, ask clarifying questions
            - Do not answer any unrelated questions yourself, always delegate to the appropriate sub-agent
            - Always answer in the context of a merchant and payment agent
            - Respond only very short summaries of tool responses to the user

            **Delegation Rules (IMPORTANT):**
            - Delegate at most twice per user message.
            - After delegating to a sub-agent, NEVER delegate again for the same request.
            - If a sub-agent returns output, respond directly to the user based on that output.
            - Do NOT re-interpret the sub-agent output as a new user instruction.
            - Avoid delegation loops at all costs.
        """,
        sub_agents=[merchant_agent, payment_agent], 
    )

    logger.info("Merchant Agent initialized with payment delegation capability")
    return root_agent
