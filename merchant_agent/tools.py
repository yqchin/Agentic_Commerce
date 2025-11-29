"""
Unified Merchant Tools - All-in-one implementation.
Combines validation, schema, and tool management in one place.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Exception Classes
# ============================================================

class MerchantToolError(Exception):
    """Base exception for merchant tool errors"""
    pass


class ValidationError(MerchantToolError):
    """Raised when merchant tool response doesn't match schema"""
    pass


# ============================================================
# Response Schema Classes (Enhanced)
# ============================================================

@dataclass
class ProductVariation:
    """Product variation option (color, size, etc.)"""
    type: str
    name: str
    price_modifier: float


@dataclass
class Product:
    """Single product data"""
    id: str
    name: str
    base_price: float
    description: str = ""
    image: str = ""  # URL to product image
    variations: Optional[List[ProductVariation]] = None
    stock_level: int = 0  # Inventory count


@dataclass
class OrderItem:
    """Single item in an order"""
    product_id: str
    quantity: int
    unit_price: float
    variations: Optional[List[Dict[str, Any]]] = None  # Selected variations


@dataclass
class ProductsResponse:
    """Response from search_products"""
    success: bool
    total_count: int
    products: List[Product]
    error: str = ""
    
    def to_json(self) -> str:
        """Convert to JSON string for API"""
        def product_to_dict(p):
            result = {
                "id": p.id,
                "name": p.name,
                "base_price": p.base_price,
                "description": p.description,
                "image": p.image,
                "stock_level": p.stock_level,
            }
            if p.variations:
                result["variations"] = [asdict(v) for v in p.variations]
            return result
        
        return json.dumps({
            "success": self.success,
            "total_count": self.total_count,
            "products": [product_to_dict(p) for p in self.products],
            "error": self.error
        })


@dataclass
class OrderResponse:
    """Response from create_order"""
    success: bool
    order_id: str
    items: List[OrderItem]
    customer_id: str
    total_amount: float
    status: str = "CREATED"
    error: str = ""
    
    def to_json(self) -> str:
        """Convert to JSON string for API"""
        def order_item_to_dict(item):
            result = {
                "product_id": item.product_id,
                "quantity": item.quantity
            }
            if item.variations:
                result["variations"] = item.variations
            return result
        
        return json.dumps({
            "success": self.success,
            "order_id": self.order_id,
            "items": [order_item_to_dict(item) for item in self.items],
            "customer_id": self.customer_id,
            "total_amount": self.total_amount,
            "status": self.status,
            "error": self.error
        })

class SchemaValidator:
    """Validates merchant tool responses"""
    
    @staticmethod
    def validate_product(product: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a product dict"""
        required = {"id", "name", "base_price", "stock_level"}
        
        if not isinstance(product, dict):
            return False, f"Product must be dict, got {type(product).__name__}"
        
        missing = required - set(product.keys())
        if missing:
            return False, f"Product missing: {missing}"
        
        if not isinstance(product["id"], str) or not product["id"].strip():
            return False, "product['id'] must be non-empty string"
        
        if not isinstance(product["name"], str) or not product["name"].strip():
            return False, "product['name'] must be non-empty string"
        
        try:
            base_price = float(product["base_price"])
            if base_price < 0:
                return False, "product['base_price'] must be >= 0"
        except (ValueError, TypeError):
            return False, f"product['base_price'] must be numeric, got {product['base_price']}"
        
        if not isinstance(product["stock_level"], int):
            return False, "product['stock_level'] must be int"
        if product["stock_level"] < 0:
            return False, "product['stock_level'] must be >= 0"
        
        if "description" in product and not isinstance(product["description"], str):
            return False, f"product['description'] must be string"
        
        if "image" in product and product["image"] is not None and not isinstance(product["image"], str):
            return False, f"product['image'] must be string or null"
        
        # Validate variations if present
        if "variations" in product and product["variations"] is not None:
            if not isinstance(product["variations"], list):
                return False, "product['variations'] must be list or null"
            for idx, var in enumerate(product["variations"]):
                if not isinstance(var, dict):
                    return False, f"variation[{idx}] must be dict"
                var_required = {"type", "name", "price_modifier"}
                var_missing = var_required - set(var.keys())
                if var_missing:
                    return False, f"variation[{idx}] missing: {var_missing}"
                if not isinstance(var["type"], str) or not var["type"].strip():
                    return False, f"variation[{idx}]['type'] must be non-empty string"
                if not isinstance(var["name"], str) or not var["name"].strip():
                    return False, f"variation[{idx}]['name'] must be non-empty string"
                try:
                    float(var["price_modifier"])
                except (ValueError, TypeError):
                    return False, f"variation[{idx}]['price_modifier'] must be numeric"
        
        return True, ""
    
    @staticmethod
    def validate_products_list(products: Any) -> Tuple[bool, str]:
        """Validate products list"""
        if not isinstance(products, list):
            return False, f"Must return list, got {type(products).__name__}"
        
        if len(products) == 0:
            return True, ""
        
        for i, product in enumerate(products):
            valid, error = SchemaValidator.validate_product(product)
            if not valid:
                return False, f"Product[{i}]: {error}"
        
        return True, ""
    
    @staticmethod
    def validate_order_item(item: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate an order item dict"""
        required = {"product_id", "quantity"}
        
        if not isinstance(item, dict):
            return False, f"Order item must be dict, got {type(item).__name__}"
        
        missing = required - set(item.keys())
        if missing:
            return False, f"Order item missing: {missing}"
        
        if not isinstance(item["product_id"], str) or not item["product_id"].strip():
            return False, "item['product_id'] must be non-empty string"
        
        try:
            qty = int(item["quantity"])
            if qty <= 0:
                return False, "item['quantity'] must be > 0"
        except (ValueError, TypeError):
            return False, f"item['quantity'] must be integer"
        
        # Validate variations if present
        if "variations" in item and item["variations"] is not None:
            if not isinstance(item["variations"], list):
                return False, "item['variations'] must be list or null"
            for idx, var in enumerate(item["variations"]):
                if not isinstance(var, dict):
                    return False, f"item variation[{idx}] must be dict"
                if "type" not in var or "name" not in var:
                    return False, f"item variation[{idx}] must have 'type' and 'name'"
                if not isinstance(var["type"], str) or not isinstance(var["name"], str):
                    return False, f"item variation[{idx}] type/name must be strings"
        
        return True, ""
    
    @staticmethod
    def validate_order_dict(order: Any) -> Tuple[bool, str]:
        """Validate order dict"""
        required = {"order_id", "items", "total_amount"}
        
        if not isinstance(order, dict):
            return False, f"Must return dict, got {type(order).__name__}"
        
        missing = required - set(order.keys())
        if missing:
            return False, f"Order missing: {missing}"
        
        if not isinstance(order["order_id"], str) or not order["order_id"].strip():
            return False, "order['order_id'] must be non-empty string"
        
        if not isinstance(order["items"], list):
            return False, f"order['items'] must be list"
        
        if len(order["items"]) == 0:
            return False, "order['items'] cannot be empty"
        
        for i, item in enumerate(order["items"]):
            valid, error = SchemaValidator.validate_order_item(item)
            if not valid:
                return False, f"Item[{i}]: {error}"
        
        try:
            total = float(order["total_amount"])
            if total < 0:
                return False, "order['total_amount'] cannot be negative"
        except (ValueError, TypeError):
            return False, f"order['total_amount'] must be numeric"
        
        return True, ""


# ============================================================
# Merchant Tools Base Class
# ============================================================

class MerchantTools(ABC):
    """
    Base class for merchant tool implementations.
    
    Merchants extend this and implement just 2 methods:
    - get_products()
    - process_new_order()
    
    Everything else is handled automatically!
    """
    
    @abstractmethod
    async def get_products(
        self, 
        query: str = "", 
        limit: int = 10,
        product_id: Optional[str] = None,
        name_contains: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        desc_contains: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search products with filters. Return list of dicts with:
        - id (str, required)
        - name (str, required)
        - base_price (numeric, required)
        - stock_level (int, required)
        - description (str, optional)
        - image (str, optional)
        - product_id (str, optional): Search by exact product ID
        - variations (list of dicts, optional)
          - Each variation: type, name, price_modifier
        """
        pass
    
    @abstractmethod
    async def process_new_order(
        self, 
        items: List[Dict[str, Any]],
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an order. items is a list of dicts with:
        - product_id (str, required)
        - quantity (int, required, > 0)
        - variations (list of dicts, optional)
          - Each variation: type, name
        
        Return dict with:
        - order_id (str, required, non-empty)
        - items (list, required, non-empty)
          - Each item: product_id, quantity, variations (optional)
        - total_amount (numeric, required, >= 0)
        - status (str, optional)
        """
        pass
    
    # ========== Internal Methods (Do Not Override) ==========
    
    async def search_products(
        self, 
        query: str = "", 
        limit: int = 10,
        product_id: Optional[str] = None,
        name_contains: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        desc_contains: Optional[str] = None
    ) -> str:
        """Internal: validates and converts get_products response"""
        # Call merchant's implementation
        products_data = await self.get_products(query, limit, product_id, name_contains, price_min, price_max, desc_contains)
        
        # Validate - will raise ValidationError if invalid
        valid, error = SchemaValidator.validate_products_list(products_data)
        if not valid:
            raise ValidationError(f"{error}")
        
        # Convert to Product objects
        products = [
            Product(
                id=p["id"],
                name=p["name"],
                base_price=float(p["base_price"]),
                description=p.get("description", ""),
                image=p.get("image"),
                variations=[
                    ProductVariation(
                        type=v["type"],
                        name=v["name"],
                        price_modifier=float(v["price_modifier"])
                    ) for v in p.get("variations", [])
                ] if p.get("variations") else None,
                stock_level=int(p["stock_level"])
            )
            for p in products_data
        ]
        
        # Return as JSON
        if len(products) == 0:
            return None
        
        response = ProductsResponse(
            success=True,
            total_count=len(products),
            products=products
        )
        output = response.to_json()
        logger.info(f"Products retrieved: {response.total_count}")
        return output
    
    async def create_order(
        self,
        items: List[Dict[str, Any]],
        customer_id: Optional[str] = None
    ) -> str:
        """Internal: validates and converts process_new_order response"""
        # Validate items before passing to merchant
        for idx, item in enumerate(items):
            valid, error = SchemaValidator.validate_order_item(item)
            if not valid:
                raise ValidationError(f"Order item[{idx}]: {error}")
        
        # Call merchant's implementation
        order_data = await self.process_new_order(items, customer_id)
        
        # Validate - will raise ValidationError if invalid
        valid, error = SchemaValidator.validate_order_dict(order_data)
        if not valid:
            raise ValidationError(f"{self.__class__.__name__}.process_new_order(): {error}")
        
        # Convert to OrderItem objects
        order_items = [
            OrderItem(
                product_id=item["product_id"],
                quantity=int(item["quantity"]),
                unit_price=float(item["unit_price"]),
                variations=item.get("variations")
            )
            for item in order_data["items"]
        ]
        
        # Return as JSON
        if len(order_items) == 0:
            return None
        
        response = OrderResponse(
            success=True,
            order_id=order_data["order_id"],
            items=order_items,
            customer_id=customer_id or "GUEST",
            total_amount=float(order_data["total_amount"]),
            status=order_data.get("status", "CREATED")
        )
        output = response.to_json()
        logger.info(f"Order created: {response.order_id} for customer {response.customer_id}")
        logger.info(f"Order details: {output}")
        return output

    async def calculate_total(
        self, 
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Args:
            items: List of dicts with product_id, quantity, variations (optional)
        
        Returns: Dict with items, total_amount
        """
        order_items = []
        total_amount = 0.0
        
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            selected_variations = item.get("variations", [])
            
            # Look up product by product_id
            products_list = await self.get_products(product_id=product_id, limit=1)
            
            if not products_list or len(products_list) == 0:
                raise ValueError(f"Product {product_id} not found")
            
            product = products_list[0]
            product_name = product["name"]
            
            # Calculate price with variations
            item_price = product["base_price"]
            if selected_variations and product.get("variations"):
                for selected_var in selected_variations:
                    # Find matching variation and add price modifier
                    for prod_var in product["variations"]:
                        if prod_var["type"] == selected_var["type"] and prod_var["name"] == selected_var["name"]:
                            item_price += prod_var["price_modifier"]
                            break
            
            # Add to order
            order_items.append({
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": item_price,
                "variations": selected_variations if selected_variations else None,
            })
            
            total_amount += item_price * quantity
        
        response = {
            "items": order_items,
            "total_amount": total_amount
        }
        
        return response

# ============================================================
# Global Tools Manager
# ============================================================

_merchant_tools: Optional[MerchantTools] = None

def set_merchant_tools(tools: MerchantTools) -> None:
    """Register merchant tools instance"""
    global _merchant_tools
    _merchant_tools = tools
    logger.info(f"Merchant tools set: {tools.__class__.__name__}")


def get_merchant_tools() -> MerchantTools:
    """Get registered merchant tools"""
    if _merchant_tools is None:
        raise RuntimeError("Merchant tools not configured. Call set_merchant_tools() first.")
    return _merchant_tools
