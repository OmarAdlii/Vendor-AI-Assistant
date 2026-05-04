from typing import List, Dict, Any
import pypdf
import pandas as pd
from io import BytesIO

class DocumentProcessor:
    """Process various document types for RAG"""
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
        
        return chunks
    
    @staticmethod
    def process_pdf(file_content: bytes) -> List[Dict[str, Any]]:
        """Extract and chunk text from PDF"""
        documents = []
        
        try:
            pdf_file = BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            
            full_text = ""
            for page_num, page in enumerate(reader.pages):
                full_text += page.extract_text() + "\n"
            
            # Chunk the text
            chunks = DocumentProcessor.chunk_text(full_text)
            
            for i, chunk in enumerate(chunks):
                documents.append({
                    'content': chunk,
                    'metadata': {
                        'source': 'pdf',
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            return documents
        
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return []
    
    @staticmethod
    def process_csv(file_content: bytes) -> List[Dict[str, Any]]:
        """Process CSV file"""
        documents = []
        
        try:
            df = pd.read_csv(BytesIO(file_content))
            
            # Convert each row to text
            for idx, row in df.iterrows():
                text = " | ".join([f"{col}: {val}" for col, val in row.items()])
                
                documents.append({
                    'content': text,
                    'metadata': {
                        'source': 'csv',
                        'row_index': idx,
                        'columns': list(df.columns)
                    }
                })
            
            return documents
        
        except Exception as e:
            print(f"Error processing CSV: {e}")
            return []
    
    @staticmethod
    def process_txt(file_content: bytes) -> List[Dict[str, Any]]:
        """Process plain text file"""
        documents = []
        
        try:
            text = file_content.decode('utf-8')
            chunks = DocumentProcessor.chunk_text(text)
            
            for i, chunk in enumerate(chunks):
                documents.append({
                    'content': chunk,
                    'metadata': {
                        'source': 'txt',
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            return documents
        
        except Exception as e:
            print(f"Error processing TXT: {e}")
            return []
    
    @staticmethod
    def process_document(file_content: bytes, content_type: str) -> List[Dict[str, Any]]:
        """Process document based on content type"""
        if 'pdf' in content_type:
            return DocumentProcessor.process_pdf(file_content)
        elif 'csv' in content_type:
            return DocumentProcessor.process_csv(file_content)
        elif 'text/plain' in content_type:
            return DocumentProcessor.process_txt(file_content)
        else:
            print(f"Unsupported content type: {content_type}")
            return []