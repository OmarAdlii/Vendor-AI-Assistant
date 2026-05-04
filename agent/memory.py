from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import asyncpg
from app.config import get_settings

settings = get_settings()
from utils.logger import get_logger
from utils.json_utils import make_serializable

logger = get_logger(__name__)

class ConversationMemory:
    """Manage conversation history in PostgreSQL (chatAi database)"""
    
    def __init__(self):
        self.max_history = 20  # Keep last 20 messages
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize connection pool to chatAi database"""
        self.pool = await asyncpg.create_pool(
            host=settings.chat_db_host,
            port=settings.chat_db_port,
            user=settings.chat_db_user,
            password=settings.chat_db_password,
            database=settings.chat_db_name,
            min_size=5,
            max_size=20
        )
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        vendor_id: Optional[str] = None
    ) -> bool:
        """Add a message to conversation history (لا يتم حذفها أبداً)"""
        try:
            query = """
                INSERT INTO chat_memory 
                (session_id, role, content, metadata, vendor_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """
            # Ensure metadata is serialized to JSON string to be compatible
            # with databases that have metadata as TEXT or JSONB.
            md = metadata or {}
            md_param = json.dumps(make_serializable(md)) if not isinstance(md, str) else md

            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    session_id, role, content, md_param, vendor_id, datetime.now()
                )
            logger.debug("Added message session=%s role=%s", session_id, role)
            return True
        except Exception as e:
            logger.exception("Error adding message to memory: %s", e)
            return False
    
    async def get_history(
        self,
        session_id: str,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            limit = limit or self.max_history
            query = """
                SELECT id, role, content, metadata, vendor_id, created_at
                FROM chat_memory
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, session_id, limit)
                results = [dict(row) for row in rows]
            # Normalize metadata: if stored as string, attempt to parse JSON
            for r in results:
                md = r.get('metadata')
                if isinstance(md, str):
                    try:
                        r['metadata'] = json.loads(md)
                    except Exception:
                        r['metadata'] = md
            # Reverse to get chronological order
            return list(reversed(results))
        except Exception as e:
            logger.exception("Error getting conversation history: %s", e)
            return []
    
    async def get_all_history(
        self,
        session_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get all conversation history for analysis (بدون حد)"""
        try:
            if start_date and end_date:
                query = """
                    SELECT id, role, content, metadata, vendor_id, created_at
                    FROM chat_memory
                    WHERE session_id = $1 
                    AND created_at BETWEEN $2 AND $3
                    ORDER BY created_at ASC
                """
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, session_id, start_date, end_date)
            else:
                query = """
                    SELECT id, role, content, metadata, vendor_id, created_at
                    FROM chat_memory
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                """
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, session_id)
                
                    results = [dict(row) for row in rows]
                for r in results:
                    md = r.get('metadata')
                    if isinstance(md, str):
                        try:
                            r['metadata'] = json.loads(md)
                        except Exception:
                            r['metadata'] = md

                return results
        except Exception as e:
            logger.exception("Error getting all history: %s", e)
            return []
    
    async def search_history(
        self,
        session_id: Optional[str] = None,
        search_text: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search conversation history for analysis"""
        try:
            conditions = []
            params = []
            param_count = 1
            
            if session_id:
                conditions.append(f"session_id = ${param_count}")
                params.append(session_id)
                param_count += 1
            
            if search_text:
                conditions.append(f"content ILIKE ${param_count}")
                params.append(f"%{search_text}%")
                param_count += 1
            
            if start_date:
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)
                param_count += 1
            
            if end_date:
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            
            query = f"""
                 SELECT id, session_id, role, content, metadata, vendor_id, created_at
                FROM chat_memory
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count}
            """
            params.append(limit)
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            for r in results:
                md = r.get('metadata')
                if isinstance(md, str):
                    try:
                        r['metadata'] = json.loads(md)
                    except Exception:
                        r['metadata'] = md

            return results
        except Exception as e:
            logger.exception("Error searching history: %s", e)
            return []
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message
                FROM chat_memory
                WHERE session_id = $1
            """
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, session_id)

            return dict(row) if row else {}
        except Exception as e:
            logger.exception("Error getting session stats: %s", e)
            return {}
    
    async def clear_history(self, session_id: str) -> bool:
        logger.warning("clear_history called for session %s - operation is a no-op", session_id)
        return True
    
    async def archive_old_sessions(self, days_old: int = 90) -> int:
        
        try:
            query = """
                WITH archived AS (
                    INSERT INTO chat_memory_archive 
                    SELECT * FROM chat_memory
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    RETURNING id
                )
                DELETE FROM chat_memory
                WHERE id IN (SELECT id FROM archived)
            """
            async with self.pool.acquire() as conn:
                result = await conn.execute(query % days_old)
                # Extract number from result like "DELETE 123"
                count = int(result.split()[-1]) if result else 0
            logger.info("archive_old_sessions: archived %d rows older than %d days", count, days_old)
            return count
        except Exception as e:
            logger.exception("Error archiving old sessions: %s", e)
            return 0
    
    async def get_recent_context(
        self,
        session_id: str,
        num_messages: int = 5
    ) -> str:
        """Get recent conversation context as formatted string"""
        history = await self.get_history(session_id, limit=num_messages)
        
        context = []
        for msg in history:
            role = msg['role'].capitalize()
            content = msg['content']
            context.append(f"{role}: {content}")
        
        return "\n".join(context)
    
    async def initialize_tables(self):
        """Create chat_memory table if it doesn't exist in chatAi database"""
        try:
            async with self.pool.acquire() as conn:
                # Main chat memory table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_memory (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        vendor_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Add vendor_id column if it doesn't exist (for existing tables)
                await conn.execute("""
                    ALTER TABLE chat_memory 
                    ADD COLUMN IF NOT EXISTS vendor_id VARCHAR(255)
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_session_id 
                    ON chat_memory(session_id)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_created_at 
                    ON chat_memory(created_at)
                """)
                
                # Archive table for old conversations
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_memory_archive (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        vendor_id VARCHAR(255),
                        created_at TIMESTAMP,
                        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Add vendor_id column to archive table if it doesn't exist
                await conn.execute("""
                    ALTER TABLE chat_memory_archive 
                    ADD COLUMN IF NOT EXISTS vendor_id VARCHAR(255)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_archive_session_id 
                    ON chat_memory_archive(session_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_archive_created_at 
                    ON chat_memory_archive(archived_at)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_vendor_id
                    ON chat_memory(vendor_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_archive_vendor_id
                    ON chat_memory_archive(vendor_id)
                """)
                
            logger.info("conversation memory tables initialized")
            return True
        except Exception as e:
            logger.exception("Error initializing tables: %s", e)
            return False

# Singleton instance
conversation_memory = ConversationMemory()