from typing import List
import openai
from app.config import get_settings

settings = get_settings()
openai.api_key = settings.openai_api_key

class EmbeddingGenerator:
    """Generate embeddings using OpenAI"""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = openai.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            response = openai.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return []