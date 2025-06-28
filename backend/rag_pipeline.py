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
from weaviate.classes.config import Configure, Property, DataType
# FIX: Import the updated WeaviateVectorStore from the new package
from langchain_weaviate import WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.docstore.document import Document
import pickle
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import weaviate
from weaviate.classes.init import Auth

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
    """Initialize Weaviate client with environment variables."""
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not url or not api_key or not openai_api_key:
        raise ValueError("WEAVIATE_URL, WEAVIATE_API_KEY, and OPENAI_API_KEY must be set.")
    
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    parsed_url = urlparse(url)
    http_host = parsed_url.hostname
    http_port = parsed_url.port or 443
    http_secure = parsed_url.scheme == 'https'
    grpc_port = 50051

    logger.info(f"Connecting to Weaviate at {http_host}:{http_port} (HTTP) and {http_host}:{grpc_port} (gRPC)")
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

    # Connect to Weaviate Cloud
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),  
    )
    print(client.is_ready())  # Should print: `True`
    
    return client 

def log_time(start_time: float, operation: str) -> float:
    """Log the time taken for an operation and return current time."""
    duration = time.time() - start_time
    logger.info(f"Time taken for {operation}: {duration:.2f} seconds")
    return time.time()

def get_cache_path(pdf_path: str) -> Path:
    """Generate a cache file path for a PDF."""
    pdf_hash = hashlib.md5(str(pdf_path).encode()).hexdigest()
    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{pdf_hash}.pickle"

def load_pdf_documents(folder_path: str, use_cache: bool = True) -> List[Document]:
    """Load PDF documents from a folder and convert them to LangChain documents."""
    pdf_dir = pathlib.Path(folder_path)
    if not pdf_dir.exists():
        raise ValueError(f"Folder not found: {folder_path}")
    
    logger.info(f"Scanning for PDF files in {folder_path}")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    documents = []
    for pdf_path in pdf_files:
        if not pdf_path.is_file():
            logger.error(f"Path is not a file: {pdf_path}")
            continue
            
        cache_path = get_cache_path(str(pdf_path))
        if use_cache and cache_path.exists():
            try:
                logger.info(f"Loading cached version of {pdf_path.name}")
                with open(cache_path, 'rb') as f:
                    documents.extend(pickle.load(f))
                continue
            except Exception as e:
                logger.warning(f"Failed to load cache for {pdf_path.name}: {str(e)}")
        
        logger.info(f"\nProcessing PDF: {pdf_path.name}")
        try:
            from PyPDF2 import PdfReader
            pdf = PdfReader(str(pdf_path))
            doc_pages = []
            for i, page in enumerate(tqdm(pdf.pages, desc=f"Reading pages from {pdf_path.name}")):
                text = page.extract_text()
                if text:
                    doc_pages.append(Document(page_content=text, metadata={"source": str(pdf_path), "page": i + 1}))
            
            if use_cache:
                with open(cache_path, 'wb') as f:
                    pickle.dump(doc_pages, f)
            
            documents.extend(doc_pages)
            logger.info(f"Successfully processed {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {str(e)}", exc_info=True)
    
    logger.info(f"\nTotal pages processed: {len(documents)}")
    return documents

def split_documents(documents: List[Document], chunk_size: int = 400, chunk_overlap: int = 100) -> List[Document]:
    """Split documents into smaller chunks."""
    logger.info(f"Splitting {len(documents)} documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} chunks.")
    return chunks

def create_vector_store(class_name: str = "PolicyChunks") -> WeaviateVectorStore:
    """Create and configure Weaviate vector store."""
    start_time = time.time()
    
    logger.info("Initializing Weaviate client")
    client = get_weaviate_client()
    log_time(start_time, "client initialization")
    
    logger.info("Initializing OpenAI embeddings model")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    if not client.collections.exists(name=class_name):
        logger.info(f"Creating new collection: {class_name}")
        client.collections.create(
            name=class_name,
            vectorizer_config=Configure.Vectorizer.text2vec_openai(),
            properties=[
                Property(name="text", data_type=DataType.TEXT, vectorize_property_name=False, skip_vectorization=False),
                Property(name="source", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="page", data_type=DataType.INT, skip_vectorization=True),
            ]
        )
        logger.info(f"Collection '{class_name}' created successfully.")
    else:
        logger.info(f"Using existing collection: {class_name}")
    
    return WeaviateVectorStore(
        client=client,
        index_name=class_name,
        text_key="text",
        embedding=embeddings,
        attributes=["source", "page"]
    )

def process_and_load_documents(folder_path: str, class_name: str = "PolicyChunks", use_cache: bool = True) -> None:
    """Process PDF documents and load them into Weaviate vector store."""
    try:
        pipeline_start = time.time()
        
        documents = load_pdf_documents(folder_path, use_cache=use_cache)
        chunks = split_documents(documents)
        vector_store = create_vector_store(class_name)
        
        logger.info(f"Adding {len(chunks)} chunks to vector store...")
        vector_store.add_documents(chunks)
        logger.info("Successfully added chunks to vector store.")
        
        log_time(pipeline_start, "Total pipeline processing")
        
    except Exception as e:
        logger.error(f"Error in document processing pipeline: {str(e)}", exc_info=True)
        raise

def test_retrieval(query: str, class_name: str = "PolicyChunks", k: int = 5) -> List[Document]:
    """Test retrieval from the vector store."""
    logger.info(f"Testing retrieval with query: '{query}'")
    start_time = time.time()
    
    try:
        vector_store = create_vector_store(class_name)
        docs = vector_store.similarity_search(query, k=k)
        
        logger.info(f"\nFound {len(docs)} relevant documents in {time.time() - start_time:.2f} seconds.")
        for i, doc in enumerate(docs, 1):
            logger.info(f"\n--- Result {i} ---")
            logger.info(f"Source: {doc.metadata.get('source', 'N/A')}")
            logger.info(f"Page: {doc.metadata.get('page', 'N/A')}")
            logger.info(f"Content: {doc.page_content[:250]}...")
        
        return docs
        
    except Exception as e:
        logger.error(f"Error during retrieval: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        logger.info("--- Starting Main Execution ---")
        start_time = time.time()
        docs_path = os.path.join(os.path.dirname(__file__), "..", "policy_docs")
        process_and_load_documents(docs_path)
        # Example of how to test retrieval
        # test_retrieval(query="What is the policy on data privacy?")
        logger.info(f"--- Main execution completed successfully in {time.time() - start_time:.2f} seconds ---")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)