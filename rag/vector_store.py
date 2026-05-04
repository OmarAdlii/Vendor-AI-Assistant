from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from app.config import get_settings
from rag.embeddings import EmbeddingGenerator

settings = get_settings()

class VectorStore:
    """Supabase vector store for RAG"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.embedding_generator = EmbeddingGenerator()
        self.table_name = "documents"
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> bool:
        """Add documents to vector store"""
        try:
            for doc in documents:
                # Generate embedding
                embedding = await self.embedding_generator.generate_embedding(
                    doc['content']
                )
                
                # Insert into Supabase
                data = {
                    'content': doc['content'],
                    'metadata': doc.get('metadata', {}),
                    'embedding': embedding
                }
                
                result = self.client.table(self.table_name).insert(data).execute()
            
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False
    
    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_embedding(query)
            
            # Call Supabase RPC function for similarity search
            result = self.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': top_k
                }
            ).execute()
            
            return result.data if result.data else []
        
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []
    
    async def delete_all_documents(self) -> bool:
        """Delete all documents (use with caution)"""
        try:
            self.client.table(self.table_name).delete().neq('id', 0).execute()
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False

# Singleton instance
vector_store = VectorStore()