from typing import List, Dict, Any
from rag.vector_store import vector_store
from rag.document_processor import DocumentProcessor

class RAGTools:
    """RAG tools for knowledge base search"""
    
    @staticmethod
    async def search_knowledge_base(
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for policies, rules, and guidelines.
        Use when users ask about business rules or platform policies.
        """
        results = await vector_store.similarity_search(
            query=query,
            top_k=top_k,
            threshold=threshold
        )
        
        return results
    
    @staticmethod
    async def add_documents_to_kb(
        file_content: bytes,
        content_type: str
    ) -> Dict[str, Any]:
        """Add documents to knowledge base"""
        # Process document
        documents = DocumentProcessor.process_document(file_content, content_type)
        
        if not documents:
            return {
                "success": False,
                "message": "Failed to process document"
            }
        
        # Add to vector store
        success = await vector_store.add_documents(documents)
        
        return {
            "success": success,
            "message": f"Added {len(documents)} chunks to knowledge base" if success else "Failed to add documents",
            "chunks_added": len(documents) if success else 0
        }