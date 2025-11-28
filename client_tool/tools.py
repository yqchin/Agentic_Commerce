"""
Tools for Merchant Agent to interact with Payment Agent and Product Services
"""

import logging
from typing import Optional, TYPE_CHECKING, List, Dict, Any
from google.adk.tools.tool_context import ToolContext
from ..tools import MerchantTools, get_merchant_tools
from ..cart_service import get_cart_service
from ..session import get_session_id
import json

logger = logging.getLogger(__name__)

# Tool: Search Products
async def search_products(
    query: str = "",
    limit: int = 10,
    product_id: Optional[str] = None,
    name_contains: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    desc_contains: Optional[str] = None,
    tool_context: ToolContext = None,
) -> str:
    """
    Search for products with optional filters
    
    Args:
        query: General product search query
        limit: Maximum number of results
        product_id: Search by exact product ID
        name_contains: Filter by name (substring match)
        price_min: Minimum price filter
        price_max: Maximum price filter
        desc_contains: Filter by description (substring match)
        tool_context: Tool execution context
        
    Returns:
        List of matching products with variations, images, and stock levels
    """
    try:
        merchant_tools = get_merchant_tools()
        logger.info(f"Searching products: query={query}, product_id={product_id}")
        
        # Call merchant's custom implementation
        result = await merchant_tools.search_products(
            query, limit, product_id, name_contains, price_min, price_max, desc_contains
        )
        
        if tool_context:
            tool_context.state["search_result"] = result

        return result

    except Exception as e:
        logger.error(f"Product search error: {e}")
        error_msg = f"Product search failed: {str(e)}"
        if tool_context:
            tool_context.state["search_result"] = error_msg
        return error_msg


# Tool: Create Order
async def create_order(
    items: List[Dict[str, Any]],
    customer_id: Optional[str] = None,
    tool_context: ToolContext = None,
) -> str:
    """
    Create a new order with specified items
    
    Args:
        items: List of order items, each with:
               - product_id (str): Product ID
               - quantity (int): Quantity to order
               - variations (list[dict], optional): Selected variations with type and name
        customer_id: Customer identifier
        tool_context: Tool execution context
        
    Returns:
        Order confirmation with total price and order ID
    """
    try:
        merchant_tools = get_merchant_tools()
        logger.info(f"Creating order with {len(items)} items")
        
        # Call merchant's custom implementation
        result = await merchant_tools.create_order(items, customer_id)
        
        if tool_context:
            tool_context.state["order_result"] = result

        return result

    except Exception as e:
        logger.error(f"Order creation error: {e}")
        error_msg = f"Order creation failed: {str(e)}"
        if tool_context:
            tool_context.state["order_result"] = error_msg
        return error_msg


# ============================================================
# Cart Tools
# ============================================================

async def add_to_cart(
    product_id: str,
    quantity: int,
    variations: Optional[List[Dict[str, str]]] = None,
    unit_price: Optional[float] = None,
    tool_context: ToolContext = None,
) -> str:
    """
    Add item to shopping cart
    
    Args:
        product_id: Product ID to add
        quantity: Quantity to add (must be > 0)
        variations: Optional product variations (list of dicts with 'type' and 'name')
        unit_price: Price per unit (optional - will be calculated if not provided)
        tool_context: Tool execution context
        
    Returns:
        Updated cart summary
    """
    try:
        # Get session_id from global state
        session_id = get_session_id()
        if unit_price is None:
            merchant_tools = get_merchant_tools()
            logger.info(f"Calculating price for {product_id} using calculate_total")
            
            try:
                # Call process_new_order just for price calculation (no order creation)
                calc_result = await merchant_tools.calculate_total(
                    items=[{
                        "product_id": product_id,
                        "quantity": 1,
                        "variations": variations or []
                    }]
                )
                logger.info(f"Price calculation result: {calc_result}")
                # Extract unit_price from the calculated order
                if calc_result and "items" in calc_result and len(calc_result["items"]) > 0:
                    order_item = calc_result["items"][0]
                    unit_price = float(order_item.get("unit_price", 0))
                    logger.info(f"Calculated unit_price for {product_id}: ${unit_price}")
                else:
                    logger.warning(f"No items returned from price calculation")
                    unit_price = 0.0
                    
            except Exception as e:
                logger.error(f"Error calculating price with process_new_order: {e}", exc_info=True)
                unit_price = 0.0
        
        cart_service = get_cart_service()
        logger.info(f"Adding to cart: {product_id} x{quantity} @ ${unit_price} (session: {session_id})")
        
        result = cart_service.add_to_cart(session_id, product_id, quantity, variations, unit_price)
        
        if tool_context:
            tool_context.state["cart_result"] = result
        
        item_count = result.get('item_count', 0)
        total = result.get('total_amount', 0)
        return f"Added {quantity} x {product_id} to cart. Cart now has {item_count} item(s), total: ${total:.2f}"

    except Exception as e:
        logger.error(f"Add to cart error: {e}", exc_info=True)
        error_msg = f"Failed to add to cart: {str(e)}"
        if tool_context:
            tool_context.state["cart_result"] = error_msg
        return error_msg


async def view_cart(
    tool_context: ToolContext = None,
) -> str:
    """
    View current shopping cart contents
    
    Args:
        tool_context: Tool execution context
        
    Returns:
        Cart contents with all items, amounts, and totals
    """
    try:
        # Get session_id from global state
        session_id = get_session_id()
        
        cart_service = get_cart_service()
        logger.info(f"Viewing cart for session {session_id}")
        
        result = cart_service.view_cart(session_id)
        
        if tool_context:
            tool_context.state["cart_result"] = result
        
        if result['item_count'] == 0:
            return "Your cart is empty."
        
        # Format cart summary with pricing
        summary = {
            "session_id": result["session_id"],
            "items": result["items"],
            "item_count": result["item_count"],
            "subtotal": result.get("subtotal", 0),
            "shipping_fee": result.get("shipping_fee", 0),
            "total_amount": result.get("total_amount", 0),
            "updated_at": result["updated_at"]
        }
        
        return json.dumps(summary, indent=2)

    except Exception as e:
        logger.error(f"View cart error: {e}")
        error_msg = f"Failed to view cart: {str(e)}"
        if tool_context:
            tool_context.state["cart_result"] = error_msg
        return error_msg


async def remove_from_cart(
    product_id: str,
    variations: Optional[List[Dict[str, str]]] = None,
    tool_context: ToolContext = None,
) -> str:
    """
    Remove item from shopping cart
    
    Args:
        product_id: Product ID to remove
        variations: Optional variations to match specific item
        tool_context: Tool execution context
        
    Returns:
        Updated cart summary
    """
    try:
        # Get session_id from global state
        session_id = get_session_id()
        
        cart_service = get_cart_service()
        logger.info(f"Removing from cart: {product_id} (session: {session_id})")
        
        result = cart_service.remove_from_cart(session_id, product_id, variations)
        
        if tool_context:
            tool_context.state["cart_result"] = result
        
        return f"Removed {product_id} from cart. Cart now has {result['item_count']} item(s)."

    except Exception as e:
        logger.error(f"Remove from cart error: {e}")
        error_msg = f"Failed to remove from cart: {str(e)}"
        if tool_context:
            tool_context.state["cart_result"] = error_msg
        return error_msg
