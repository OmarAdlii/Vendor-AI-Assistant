from typing import Dict, Any, Optional, List
from mcp_server.database import db_manager

class DatabaseTools:
    """Database query tools for MCP server"""
    
    @staticmethod
    async def query_stores(
        store_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        module_id: Optional[int] = None,
        sub_module_id: Optional[int] = None,
        status: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Query store information"""
        conditions = {
            "store_id": store_id,
            "vendor_id": vendor_id,
            "module_id": module_id,
            "sub_module_id": sub_module_id,
            "status": status
        }
        return await db_manager.query_table('"Stores"', where_conditions=conditions)
    
    @staticmethod
    async def query_orders(
        order_id: Optional[int] = None,
        store_id: Optional[int] = None,
        module_id: Optional[int] = None,
        order_status: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query order data"""
        conditions = {
            "order_id": order_id,
            "store_id": store_id,
            "module_id": module_id,
            "order_status": order_status,
            "payment_method": payment_method
        }
        return await db_manager.query_table('"Orders"', where_conditions=conditions)
    
    @staticmethod
    async def query_items(
        item_id: Optional[int] = None,
        store_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query product/item catalog"""
        conditions = {
            "item_id": item_id,
            "store_id": store_id
        }
        return await db_manager.query_table('"Items"', where_conditions=conditions)
    
    @staticmethod
    async def query_reviews(
        review_id: Optional[int] = None,
        item_id: Optional[int] = None,
        store_id: Optional[int] = None,
        order_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query customer reviews"""
        conditions = {
            "review_id": review_id,
            "item_id": item_id,
            "store_id": store_id,
            "order_id": order_id
        }
        return await db_manager.query_table('"Reviews"', where_conditions=conditions)
    
    @staticmethod
    async def query_coupons(
        coupon_id: Optional[int] = None,
        code: Optional[str] = None,
        store_id: Optional[int] = None,
        module_id: Optional[int] = None,
        status: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Query promotional coupons"""
        conditions = {
            "coupon_id": coupon_id,
            "code": code,
            "store_id": store_id,
            "module_id": module_id,
            "status": status
        }
        return await db_manager.query_table('"Coupons"', where_conditions=conditions, limit=500)
    
    @staticmethod
    async def query_discounts(
        discount_id: Optional[int] = None,
        store_id: Optional[int] = None,
        discount: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Query store-level discounts"""
        conditions = {
            "discount_id": discount_id,
            "store_id": store_id,
            "discount": discount
        }
        return await db_manager.query_table('"Discounts"', where_conditions=conditions)
    
    @staticmethod
    async def query_refunds(
        refund_id: Optional[int] = None,
        order_id: Optional[int] = None,
        refund_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query refund requests"""
        conditions = {
            "refund_id": refund_id,
            "order_id": order_id,
            "refund_status": refund_status
        }
        return await db_manager.query_table('"Refunds"', where_conditions=conditions)
    
    @staticmethod
    async def query_vmbe(
        store_id: Optional[int] = None,
        vendor_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query vendor/store performance scores"""
        conditions = {
            "store_id": store_id,
            "vendor_id": vendor_id
        }
        return await db_manager.query_table('"VMBE"', where_conditions=conditions)
    
    @staticmethod
    async def query_kpis(
        module_id: Optional[int] = None,
        sub_module_id: Optional[int] = None,
        utilite: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query KPI definitions with their sub-goals and weights for performance evaluation"""
        conditions = {
            "module_id": module_id,
            "sub_module_id": sub_module_id,
            "utilite": utilite
        }
        return await db_manager.query_join_kpis_sub(where_conditions=conditions)
    
    @staticmethod
    async def query_modules(
        module_id: Optional[int] = None,
        status: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Query business modules"""
        conditions = {
            "module_id": module_id,
            "status": status
        }
        return await db_manager.query_table('"Module"', where_conditions=conditions)
    
    @staticmethod
    async def query_sub_modules(
        sub_module_id: Optional[int] = None,
        module_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query sub-modules"""
        conditions = {
            "sub_module_id": sub_module_id,
            "module_id": module_id
        }
        return await db_manager.query_table('"Sub_module"', where_conditions=conditions)
    
    @staticmethod
    async def query_temp_products(
        temp_product_id: Optional[int] = None,
        store_id: Optional[int] = None,
        status: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Query temporary product submissions"""
        conditions = {
            "temp_prodcut_id": temp_product_id,
            "store_id": store_id,
            "status": status
        }
        return await db_manager.query_table('"Temp_prodcuts"', where_conditions=conditions)
    
    @staticmethod
    async def query_vendors(
        vendor_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query vendor details"""
        conditions = {
            "vendor_id": vendor_id
        }
        return await db_manager.query_table('"Vendors"', where_conditions=conditions)
    
    @staticmethod
    async def get_vendor_ids(
        vendor_id: int
    ) -> List[Dict[str, Any]]:
        """Get store, module, and sub-module IDs for a vendor"""
        conditions = {
            "vendor_id": vendor_id
        }
        return await db_manager.query_table('"Stores"', where_conditions=conditions)