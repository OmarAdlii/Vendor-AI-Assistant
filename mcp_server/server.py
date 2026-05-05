from typing import Dict, Any, List
from mcp_server.tools.database_tools import DatabaseTools
from mcp_server.tools.rag_tools import RAGTools
from mcp_server.database import db_manager
import json
from utils.logger import get_logger

logger = get_logger(__name__)
import inspect
from typing import get_origin, get_args

class MCPServer:
    """MCP Server implementation"""
    
    def __init__(self):
        self.db_tools = DatabaseTools()
        self.rag_tools = RAGTools()
        self.tools_registry = self._register_tools()
        self._initialized = False
        self.db_connected = False
    
    async def initialize(self):
        """Initialize MCP Server and database connection"""
        if not self._initialized:
            try:
                await db_manager.connect()
                self.db_connected = True
                logger.info("Database connection established for MCP Server")
            except Exception as e:
                # Log but continue in degraded mode so tools can be listed and non-DB tools used
                logger.warning("Could not connect to database: %s", e)
                self.db_connected = False

            self._initialized = True
            logger.info("MCP Server initialized (degraded mode=%s)", not self.db_connected)
    
    def _register_tools(self) -> Dict[str, Any]:
        """Register all available tools"""
        return {
            # Database tools
            "query_stores": {
                "function": self.db_tools.query_stores,
                "description": "Query store information",
                "parameters": ["store_id", "vendor_id", "module_id", "sub_module_id", "status"],
                "requires_db": True
            },
            "query_orders": {
                "function": self.db_tools.query_orders,
                "description": "Query order data",
                "parameters": ["order_id", "store_id", "module_id", "order_status", "payment_method"]
            },
            "query_items": {
                "function": self.db_tools.query_items,
                "description": "Query product/item catalog",
                "parameters": ["item_id", "store_id"]
            },
            "query_reviews": {
                "function": self.db_tools.query_reviews,
                "description": "Query customer reviews",
                "parameters": ["review_id", "item_id", "store_id", "order_id"]
            },
            "query_coupons": {
                "function": self.db_tools.query_coupons,
                "description": "Query promotional coupons",
                "parameters": ["coupon_id", "code", "store_id", "module_id", "status"]
            },
            "query_discounts": {
                "function": self.db_tools.query_discounts,
                "description": "Query store discounts",
                "parameters": ["discount_id", "store_id", "discount"]
            },
            "query_refunds": {
                "function": self.db_tools.query_refunds,
                "description": "Query refund requests",
                "parameters": ["refund_id", "order_id", "refund_status"]
            },
            "query_vmbe": {
                "function": self.db_tools.query_vmbe,
                "description": "Query vendor performance scores",
                "parameters": ["store_id", "vendor_id"]
            },
            "query_kpis": {
                "function": self.db_tools.query_kpis,
                "description": "Query KPI definitions with their sub-goals and weights for performance evaluation. Use this tool when you need to understand KPI structures, their weights in final evaluation, and associated sub-goals with their individual weights.",
                "parameters": ["module_id", "sub_module_id", "utilite"]
            },
            "query_modules": {
                "function": self.db_tools.query_modules,
                "description": "Query business modules",
                "parameters": ["module_id", "status"]
            },
            "query_sub_modules": {
                "function": self.db_tools.query_sub_modules,
                "description": "Query sub-modules",
                "parameters": ["sub_module_id", "module_id"]
            },
            "query_temp_products": {
                "function": self.db_tools.query_temp_products,
                "description": "Query temporary product submissions",
                "parameters": ["temp_product_id", "store_id", "status"]
            },
            "query_vendors": {
                "function": self.db_tools.query_vendors,
                "description": "Query vendor details",
                "parameters": ["vendor_id"]
            },
            "get_vendor_ids": {
                "function": self.db_tools.get_vendor_ids,
                "description": "Get store, module IDs for vendor",
                "parameters": ["vendor_id"],
                "requires_db": True
            },
            # RAG tools
            "search_knowledge_base": {
                "function": self.rag_tools.search_knowledge_base,
                "description": "Search knowledge base for policies and rules",
                "parameters": ["query", "top_k", "threshold"],
                "requires_db": False
            }
            ,
            # Lightweight ping tool for local testing without DB
            "ping": {
                "function": (lambda: None),
                "description": "Lightweight ping tool for local checks",
                "parameters": [],
                "requires_db": False
            }
        }
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        try:
            # Ensure MCP Server is initialized
            await self.initialize()
            logger.info("execute_tool called: %s", tool_name)
            logger.debug("parameters: %s", parameters)
            if tool_name not in self.tools_registry:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found"
                }
            tool = self.tools_registry[tool_name]
            # If tool requires DB but DB is not connected, return a clear error
            if tool.get("requires_db") and not self.db_connected:
                return {
                    "success": False,
                    "error": "Database is not available; tool requires DB connection",
                    "tool_name": tool_name
                }

            func = tool["function"]
            # If ping tool, return simple response
            if tool_name == "ping":
                logger.info("ping tool request")
                return {"success": True, "tool_name": "ping", "data": {"message": "pong"}}

            # Filter parameters to only include those defined for this tool
            valid_params = {
                k: v for k, v in parameters.items()
                if k in tool["parameters"] and v is not None
            }
            
            # Execute the tool
            result = await func(**valid_params)
            # Coerce parameter types based on function annotations when possible
            try:
                sig = inspect.signature(func)
                coerced_params = {}
                for k, v in valid_params.items():
                    if k in sig.parameters:
                        ann = sig.parameters[k].annotation
                        target = None
                        # Handle Optional/Union annotations
                        origin = get_origin(ann)
                        if origin is None:
                            target = ann
                        elif origin is list or origin is dict:
                            target = ann
                        else:
                            # Union[...] or Optional[...] -> pick first non-None arg
                            args = get_args(ann)
                            for a in args:
                                if a is not type(None):
                                    target = a
                                    break

                        # Perform basic coercions
                        coerced_value = v
                        if target in (int, float, bool, str):
                            try:
                                if target is int:
                                    coerced_value = int(v)
                                elif target is float:
                                    coerced_value = float(v)
                                elif target is bool:
                                    if isinstance(v, str):
                                        coerced_value = v.lower() in ("1", "true", "yes", "y")
                                    else:
                                        coerced_value = bool(v)
                                elif target is str:
                                    coerced_value = str(v)
                            except Exception:
                                coerced_value = v

                        coerced_params[k] = coerced_value
                    else:
                        coerced_params[k] = v
                valid_params = coerced_params
            except Exception:
                # If any reflection/coercion fails, fall back to original params
                pass

            logger.debug("executing tool %s with params: %s", tool_name, valid_params)
            # Execute the tool
            result = await func(**valid_params)
            logger.info("tool %s executed; success=%s", tool_name, result.get("success") if isinstance(result, dict) else True)
            
            return {
                "success": True,
                "tool_name": tool_name,
                "data": result
            }
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f" Tool execution error: {error_trace}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for name, tool in self.tools_registry.items()
        ]

# Singleton instance
mcp_server = MCPServer()