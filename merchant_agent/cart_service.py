"""
Cart Service - In-memory cart management for merchant agent
Stores cart data per session without database
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CartService:
    """
    Manages shopping carts for multiple sessions in memory.
    Each session has its own cart identified by session_id.
    """
    
    def __init__(self):
        # In-memory storage: {session_id: cart_data}
        self._carts: Dict[str, Dict[str, Any]] = {}
        # Shipping calculator: override with custom function if needed
        self.shipping_calculator = self._default_shipping_calculator
        logger.info("CartService initialized")
    
    def add_to_cart(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
        variations: Optional[List[Dict[str, str]]] = None,
        unit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Add item to cart. If item exists, update quantity.
        
        Args:
            session_id: User session identifier
            product_id: Product ID to add
            quantity: Quantity to add (must be > 0)
            variations: Optional product variations
            unit_price: Price per unit (optional, for tracking amounts)
            
        Returns:
            Updated cart data
        """
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        
        # Initialize cart if doesn't exist
        if session_id not in self._carts:
            self._carts[session_id] = {
                "session_id": session_id,
                "items": [],
                "shipping_fee": 0.0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        
        cart = self._carts[session_id]
        
        # Check if item already exists (same product_id and variations)
        existing_item = None
        for item in cart["items"]:
            if item["product_id"] == product_id:
                # Compare variations
                item_vars = item.get("variations") or []
                new_vars = variations or []
                if self._variations_match(item_vars, new_vars):
                    existing_item = item
                    break
        
        if existing_item:
            # Update quantity
            existing_item["quantity"] += quantity
            if "unit_price" in existing_item:
                existing_item["amount"] = existing_item["unit_price"] * existing_item["quantity"]
            logger.info(f"Updated cart item {product_id} quantity to {existing_item['quantity']}")
        else:
            # Add new item
            item_dict = {
                "product_id": product_id,
                "quantity": quantity,
                "variations": variations or []
            }
            # Include unit_price if provided
            if unit_price is not None:
                item_dict["unit_price"] = unit_price
                item_dict["amount"] = unit_price * quantity
            
            cart["items"].append(item_dict)
            logger.info(f"Added new item {product_id} to cart")
        
        cart["updated_at"] = datetime.now().isoformat()
        
        return self._get_cart_summary(session_id)
    
    def view_cart(self, session_id: str) -> Dict[str, Any]:
        """
        Get cart contents for a session.
        
        Args:
            session_id: User session identifier
            
        Returns:
            Cart data with items
        """
        if session_id not in self._carts:
            return {
                "session_id": session_id,
                "items": [],
                "item_count": 0,
                "message": "Cart is empty"
            }
        
        return self._get_cart_summary(session_id)
    
    def remove_from_cart(
        self,
        session_id: str,
        product_id: str,
        variations: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Remove item from cart.
        
        Args:
            session_id: User session identifier
            product_id: Product ID to remove
            variations: Optional variations to match specific item
            
        Returns:
            Updated cart data
        """
        if session_id not in self._carts:
            return {
                "session_id": session_id,
                "items": [],
                "item_count": 0,
                "message": "Cart is empty"
            }
        
        cart = self._carts[session_id]
        original_count = len(cart["items"])
        
        # Remove matching item
        cart["items"] = [
            item for item in cart["items"]
            if not (
                item["product_id"] == product_id and
                self._variations_match(item.get("variations", []), variations or [])
            )
        ]
        
        removed_count = original_count - len(cart["items"])
        
        if removed_count > 0:
            cart["updated_at"] = datetime.now().isoformat()
            logger.info(f"Removed {removed_count} item(s) from cart")
        else:
            logger.info(f"Item {product_id} not found in cart")
        
        return self._get_cart_summary(session_id)
    
    def set_shipping_calculator(self, calculator_func):
        """
        Set a custom shipping calculator function.
        
        Args:
            calculator_func: Function that takes (subtotal, item_count, items) and returns shipping fee
        """
        self.shipping_calculator = calculator_func
        logger.info("Custom shipping calculator set")
    
    def _default_shipping_calculator(self, subtotal: float, item_count: int, items: List[Dict]) -> float:
        """
        Default shipping calculator:
        - Free shipping for orders over $50
        - $5 for orders under $50
        - Extra $2 per item after the first
        
        Args:
            subtotal: Cart subtotal (before shipping)
            item_count: Number of items in cart
            items: List of cart items
            
        Returns:
            Shipping fee amount
        """
        if subtotal >= 50.0:
            return 0.0  # Free shipping for $50+
        
        base_fee = 5.0
        additional_fee = max(0, (item_count - 1)) * 0.5
        
        return base_fee + additional_fee
    
    def _recalculate_shipping(self, session_id: str) -> float:
        """
        Recalculate shipping fee based on current cart contents.
        
        Args:
            session_id: User session identifier
            
        Returns:
            New shipping fee amount
        """
        if session_id not in self._carts:
            return 0.0
        
        cart = self._carts[session_id]
        items = cart.get("items", [])
        
        # Calculate subtotal
        subtotal = sum(item.get("amount", 0) for item in items)
        item_count = len(items)
        
        # Use the shipping calculator
        shipping_fee = self.shipping_calculator(subtotal, item_count, items)
        
        return max(0.0, shipping_fee)
    
    def _variations_match(
        self,
        vars1: List[Dict[str, str]],
        vars2: List[Dict[str, str]]
    ) -> bool:
        """Check if two variation lists are equivalent"""
        if len(vars1) != len(vars2):
            return False
        
        # Sort and compare
        sorted1 = sorted(vars1, key=lambda x: (x.get("type", ""), x.get("name", "")))
        sorted2 = sorted(vars2, key=lambda x: (x.get("type", ""), x.get("name", "")))
        
        return sorted1 == sorted2
    
    def _get_cart_summary(self, session_id: str) -> Dict[str, Any]:
        """Get cart summary with item count, subtotal, shipping, and total"""
        cart = self._carts.get(session_id, {"items": [], "shipping_fee": 0.0})
        
        # Calculate subtotal from items with amounts
        subtotal = 0.0
        for item in cart.get("items", []):
            if "amount" in item:
                subtotal += item["amount"]
        
        # Auto-recalculate shipping based on cart contents
        shipping_fee = self._recalculate_shipping(session_id)
        
        total_amount = subtotal + shipping_fee
        
        return {
            "session_id": session_id,
            "items": cart.get("items", []),
            "item_count": len(cart.get("items", [])),
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
            "updated_at": cart.get("updated_at", "")
        }


# Global cart service instance
_cart_service: Optional[CartService] = None


def get_cart_service() -> CartService:
    """Get or create the global cart service instance"""
    global _cart_service
    if _cart_service is None:
        _cart_service = CartService()
    return _cart_service
