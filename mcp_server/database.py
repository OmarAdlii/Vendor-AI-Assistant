import asyncpg
from typing import List, Dict, Any, Optional
from app.config import get_settings

settings = get_settings()
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False
    
    async def connect(self):
        """Initialize connection pool"""
        if self._connected and self.pool:
            return  # Already connected
        
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=5,
                max_size=20
            )
            self._connected = True
            print(f" Database pool created for {settings.postgres_db}")
        except Exception as e:
            print(f" Failed to connect to database: {e}")
            raise
    
    async def ensure_connected(self):
        """Ensure database is connected before using"""
        if not self._connected or not self.pool:
            await self.connect()
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self._connected = False
    
    async def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        await self.ensure_connected()
        logger.debug("execute_query: %s params=%s", query, params)
        async with self.pool.acquire() as conn:
            try:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.exception("Query failed: %s", e)
                raise
    
    async def execute_update(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> str:
        """Execute INSERT/UPDATE/DELETE query"""
        await self.ensure_connected()
        logger.debug("execute_update: %s params=%s", query, params)
        async with self.pool.acquire() as conn:
            try:
                if params:
                    result = await conn.execute(query, *params)
                else:
                    result = await conn.execute(query)
                return result
            except Exception as e:
                logger.exception("Update failed: %s", e)
                raise
    
    async def query_table(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where_conditions: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query table with optional filters"""
        await self.ensure_connected()
        
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table}"
        params = []
        
        if where_conditions:
            conditions = []
            param_idx = 1
            for key, value in where_conditions.items():
                if value is not None:
                    conditions.append(f"{key} = ${param_idx}")
                    params.append(value)
                    param_idx += 1
            
            if conditions:
                query += " WHERE " + " OR ".join(conditions)
        
        query += f" LIMIT {limit}"
        
        return await self.execute_query(query, tuple(params) if params else None)
    
    async def query_join_kpis_sub(
        self,
        where_conditions: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query KPIS table joined with KPIS_Sub table"""
        await self.ensure_connected()
        
        # Get the primary key column name for KPIS table
        col_rows = await self.execute_query(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'KPIS'"
        )
        cols_found = {r.get('column_name') for r in col_rows}
        if 'kpis_id' in cols_found:
            pk_col = 'kpis_id'
        elif 'kpi_id' in cols_found:
            pk_col = 'kpi_id'
        elif 'id' in cols_found:
            pk_col = 'id'
        else:
            pk_col = 'kpis_id'  # fallback
        
        # Select specific columns: from KPIS (name, weight), from KPIS_Sub (weight as sub_weight, goal)
        query = f"""
        SELECT 
            k.name, 
            k.wight AS kpi_weight, 
            s.wight AS sub_weight, 
            s.goal
        FROM "KPIS" k 
        LEFT JOIN "KPIS_Sub" s ON s.kpis_id = k."{pk_col}"
        """
        
        params = []
        param_idx = 1
        
        if where_conditions:
            conditions = []
            for key, value in where_conditions.items():
                if value is not None:
                    # Handle table prefixes for join conditions
                    if key in ['module_id', 'sub_module_id', 'utilite']:
                        conditions.append(f"k.{key} = ${param_idx}")
                    else:
                        conditions.append(f"{key} = ${param_idx}")
                    params.append(value)
                    param_idx += 1
            
            if conditions:
                query += " WHERE " + " OR ".join(conditions)
        
        query += f" LIMIT {limit}"
        
        return await self.execute_query(query, tuple(params) if params else None)

# Singleton instance
db_manager = DatabaseManager()