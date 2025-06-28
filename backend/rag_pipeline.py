import os
import pathlib
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict
from tqdm import tqdm
from dotenv import load_dotenv
import weaviate
from weaviate.util import get_valid_uuid
from langchain_community.vectorstores.weaviate import Weaviate as WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.docstore.document import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

def get_weaviate_client() -> weaviate.Client:
    """Initialize Weaviate client with environment variables.
    
    Returns:
        weaviate.Client: Configured Weaviate client
    """
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not url:
        raise ValueError("WEAVIATE_URL environment variable is required")
    if not api_key:
        raise ValueError("WEAVIATE_API_KEY environment variable is required")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Ensure URL has https:// prefix
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    logger.info(f"Connecting to Weaviate at {url}")    
    return weaviate.Client(
        url=url,
        auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
        additional_headers={
            "X-OpenAI-Api-Key": openai_api_key  # For text2vec-openai
        }
    )

def log_time(start_time: float, operation: str) -> float:
    """Log the time taken for an operation and return current time.
    
    Args:
        start_time (float): Start time from time.time()
        operation (str): Name of the operation completed
        
    Returns:
        float: Current time for chaining
    """
    duration = time.time() - start_time
    logger.info(f"Time taken for {operation}: {duration:.2f} seconds")
    return time.time()

import pickle
import hashlib
from pathlib import Path

def get_cache_path(pdf_path: str) -> Path:
    """Generate a cache file path for a PDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Path: Path where the cache file should be stored
    """
    # Create hash of the PDF path to use as cache filename
    pdf_hash = hashlib.md5(str(pdf_path).encode()).hexdigest()
    # Use absolute path to create cache directory
    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{pdf_hash}.pickle"

def load_pdf_documents(folder_path: str, use_cache: bool = True) -> List[Document]:
    """Load PDF documents from a folder and convert them to LangChain documents.
    
    Args:
        folder_path (str): Path to folder containing PDF files
        use_cache (bool, optional): Whether to use cached results. Defaults to True.
        
    Returns:
        List[Document]: List of loaded and processed documents
    """
    pdf_dir = pathlib.Path(folder_path)
    if not pdf_dir.exists():
        raise ValueError(f"Folder not found: {folder_path}")
    
    logger.info(f"Scanning for PDF files in {folder_path}")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    documents = []
    total_pages = 0
    total_characters = 0
    total_start_time = time.time()
    
    for pdf_path in pdf_files:
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            continue
            
        if not pdf_path.is_file():
            logger.error(f"Path exists but is not a file: {pdf_path}")
            continue
            
        cache_path = get_cache_path(str(pdf_path))
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        
        # Try to load from cache first
        if use_cache and cache_path.exists():
            try:
                logger.info(f"Loading cached version of {pdf_path.name}")
                with open(cache_path, 'rb') as f:
                    doc_pages = pickle.load(f)
                logger.info(f"Successfully loaded {len(doc_pages)} pages from cache")
                documents.extend(doc_pages)
                total_pages += len(doc_pages)
                total_characters += sum(len(page.page_content) for page in doc_pages)
                continue
            except Exception as e:
                logger.warning(f"Failed to load cache for {pdf_path.name}: {str(e)}")
        
        # Verify file is accessible
        try:
            with open(pdf_path, 'rb') as f:
                f.read(1024)
        except Exception as e:
            logger.error(f"Cannot read PDF file {pdf_path}: {str(e)}")
            continue
            
        logger.info(f"\nProcessing PDF: {pdf_path.name} (Size: {file_size_mb:.2f}MB)")
        logger.info(f"Full PDF path: {pdf_path.absolute()}")
        file_start_time = time.time()
        
        try:
            # Load PDF
            load_start_time = time.time()
            logger.info(f"Starting to load PDF from path: {str(pdf_path)}")
            
            # Custom loading with progress tracking
            from PyPDF2 import PdfReader
            doc_pages = []
            pdf = PdfReader(str(pdf_path))
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} pages")
            
            for page_num in tqdm(range(total_pages), desc="Reading PDF pages"):
                page = pdf.pages[page_num]
                text = page.extract_text()
                doc_pages.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(pdf_path),
                            "page": page_num + 1
                        }
                    )
                )
                if page_num % 10 == 0:  # Log every 10 pages
                    logger.info(f"Processed page {page_num + 1}/{total_pages}")
            logger.info("Finished reading PDF pages")
            
            # Debug: Check first page content
            if doc_pages:
                first_page = doc_pages[0]
                content_preview = first_page.page_content[:200] if first_page.page_content else "No content"
                logger.info(f"First page content preview: {content_preview}...")
            else:
                logger.warning("No pages were loaded from the PDF")
                
            logger.info(f"Time taken to load PDF: {time.time() - load_start_time:.2f} seconds")
            
            # Calculate statistics
            stats_start_time = time.time()
            pages_count = len(doc_pages)
            chars_count = sum(len(page.page_content) for page in doc_pages)
            avg_chars_per_page = chars_count / pages_count if pages_count > 0 else 0
            
            logger.info(f"PDF Statistics for {pdf_path.name}:")
            logger.info(f"  - Pages: {pages_count}")
            logger.info(f"  - Total characters: {chars_count:,}")
            logger.info(f"  - Average characters per page: {avg_chars_per_page:.0f}")
            logger.info(f"  - Processing speed: {file_size_mb / (time.time() - file_start_time):.2f} MB/second")
            
            # Track metadata
            for i, page in enumerate(doc_pages, 1):
                page.metadata.update({
                    'file_name': pdf_path.name,
                    'file_size': file_size_mb,
                    'total_pages': pages_count,
                    'page_number': i,
                    'chars_in_page': len(page.page_content),
                    'processing_time': time.time() - file_start_time
                })
            
            # Save to cache
            if use_cache:
                try:
                    logger.info(f"Saving processed PDF to cache: {cache_path}")
                    with open(cache_path, 'wb') as f:
                        pickle.dump(doc_pages, f)
                    logger.info("Successfully saved to cache")
                except Exception as e:
                    logger.warning(f"Failed to save cache for {pdf_path.name}: {str(e)}")
            
            documents.extend(doc_pages)
            total_pages += pages_count
            total_characters += chars_count
            
            logger.info(f"Successfully processed {pdf_path.name}")
            logger.info(f"Time taken for this file: {time.time() - file_start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {str(e)}", exc_info=True)
            raise
    
    total_time = time.time() - total_start_time
    mb_per_second = sum(p.stat().st_size for p in pdf_files) / (1024 * 1024) / total_time
    
    logger.info("\nProcessing Summary:")
    logger.info(f"Total PDFs processed: {len(pdf_files)}")
    logger.info(f"Total pages processed: {total_pages}")
    logger.info(f"Total characters processed: {total_characters:,}")
    logger.info(f"Average characters per page: {(total_characters/total_pages):.0f}")
    logger.info(f"Total processing time: {total_time:.2f} seconds")
    logger.info(f"Average processing speed: {mb_per_second:.2f} MB/second")
    
    return documents

def split_documents(documents: List[Document], chunk_size: int = 400, chunk_overlap: int = 100) -> List[Document]:
    """Split documents into smaller chunks for better processing.
    
    Args:
        documents (List[Document]): List of documents to split
        chunk_size (int, optional): Size of each chunk. Defaults to 400.
        chunk_overlap (int, optional): Overlap between chunks. Defaults to 100.
        
    Returns:
        List[Document]: List of split documents
    """
    logger.info(f"Splitting {len(documents)} documents into chunks (size={chunk_size}, overlap={chunk_overlap})")
    start_time = time.time()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    
    duration = time.time() - start_time
    logger.info(f"Created {len(chunks)} chunks in {duration:.2f} seconds")
    logger.info(f"Processing speed: {len(documents) / duration:.2f} documents/second")
    
    return chunks

def create_vector_store(class_name: str = "PolicyChunks") -> WeaviateVectorStore:
    """Create and configure Weaviate vector store.
    
    Args:
        class_name (str, optional): Name of the Weaviate class. Defaults to "PolicyChunks".
        
    Returns:
        WeaviateVectorStore: Configured vector store
    """
    start_time = time.time()
    
    logger.info("Initializing Weaviate client")
    client = get_weaviate_client()
    client_time = log_time(start_time, "client initialization")
    
    logger.info("Initializing OpenAI embeddings model")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    embeddings_time = log_time(client_time, "embeddings initialization")
    
    try:
        # Create schema if it doesn't exist
        if not client.schema.exists(class_name):
            logger.info(f"Creating new schema: {class_name}")
            schema_obj = {
                "class": class_name,
                "vectorizer": "text2vec-openai",
                "properties": [
                    {
                        "name": "text",
                        "dataType": ["text"],
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False
                            }
                        }
                    },
                    {
                        "name": "source",
                        "dataType": ["text"],
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True
                            }
                        }
                    },
                    {
                        "name": "page",
                        "dataType": ["int"],
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": True
                            }
                        }
                    }
                ]
            }
            collection = client.schema.create_class(schema_obj
            )
            logger.info(f"Collection {class_name} created successfully")
            log_time(embeddings_time, "collection creation")
        else:
            logger.info(f"Using existing collection: {class_name}")
        
        # Use the v4 client directly with LangChain
        return WeaviateVectorStore(
            client=client,
            index_name=class_name,
            text_key="text",
            embedding=embeddings,
            attributes=["source", "page"]
        )
    finally:
        pass  # Client cleanup not needed in v4

def process_and_load_documents(folder_path: str, class_name: str = "PolicyChunks", use_cache: bool = True) -> None:
    """Process PDF documents and load them into Weaviate vector store.
    
    Args:
        folder_path (str): Path to folder containing PDF files
        class_name (str, optional): Name of the Weaviate class. Defaults to "PolicyChunks".
        use_cache (bool, optional): Whether to use caching for PDF processing. Defaults to True.
    """
    try:
        logger.info("Starting document processing pipeline")
        pipeline_start = time.time()
        
        # Load documents
        load_start = time.time()
        documents = load_pdf_documents(folder_path, use_cache=use_cache)
        logger.info(f"Successfully loaded {len(documents)} documents")
        split_start = log_time(load_start, "document loading")
        
        # Split into chunks
        chunks = split_documents(documents)
        logger.info(f"Successfully split into {len(chunks)} chunks")
        store_start = log_time(split_start, "document splitting")
        
        # Create vector store and add documents
        logger.info("Creating/accessing vector store")
        vector_store = create_vector_store(class_name)
        embed_start = log_time(store_start, "vector store creation")
        
        logger.info("Adding documents to vector store")
        vector_store.add_documents(chunks)
        logger.info(f"Successfully added {len(chunks)} chunks to vector store class '{class_name}'")
        log_time(embed_start, "document embedding and storage")
        
        # Log total pipeline time
        total_time = time.time() - pipeline_start
        logger.info(f"\nTotal pipeline processing time: {total_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in document processing pipeline: {str(e)}", exc_info=True)
        raise

def test_retrieval(query: str, class_name: str = "PolicyChunks", k: int = 5) -> List[Document]:
    """Test retrieval from the vector store using a query.
    
    Args:
        query (str): The query to search for
        class_name (str, optional): Name of the Weaviate class. Defaults to "PolicyChunks".
        k (int, optional): Number of results to return. Defaults to 5.
        
    Returns:
        List[Document]: List of relevant documents
    """
    logger.info(f"Testing retrieval with query: {query}")
    start_time = time.time()
    
    try:
        # Initialize vector store
        vector_store = create_vector_store(class_name)
        
        # Perform similarity search
        docs = vector_store.similarity_search(query, k=k)
        
        # Log results
        logger.info(f"\nFound {len(docs)} relevant documents in {time.time() - start_time:.2f} seconds")
        for i, doc in enumerate(docs, 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
            logger.info(f"Page: {doc.metadata.get('page', 'Unknown')}")
            logger.info(f"Content preview: {doc.page_content[:200]}...")
        
        return docs
        
    except Exception as e:
        logger.error(f"Error during retrieval: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting main execution")
        start_time = time.time()
        process_and_load_documents(os.path.join(os.path.dirname(__file__), "..", "policy_docs"))
        logger.info(f"Main execution completed successfully in {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)
        raise
