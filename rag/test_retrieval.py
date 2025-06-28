import os
import logging
import time
import argparse
from typing import List
from langchain.docstore.document import Document
from rag_pipeline import test_retrieval

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_retrieval_test(query: str, k: int = 5) -> List[Document]:
    """Run a retrieval test with the given query.
    
    Args:
        query (str): The query to test
        k (int, optional): Number of results to return. Defaults to 5.
    
    Returns:
        List[Document]: List of retrieved documents
    """
    try:
        logger.info("Starting retrieval test")
        start_time = time.time()
        
        # Run the retrieval test directly
        results = test_retrieval(query, k=k)
        logger.info(f"Retrieval completed in {time.time() - start_time:.2f} seconds")
        return results
        
    except Exception as e:
        logger.error(f"Retrieval test failed: {str(e)}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='Test RAG retrieval with a query')
    parser.add_argument('--query', type=str, default="What are the requirements for mortgage insurance?",
                      help='Query to test retrieval (default: mortgage insurance requirements)')
    parser.add_argument('--results', type=int, default=5,
                      help='Number of results to return (default: 5)')
    args = parser.parse_args()
    
    try:
        run_retrieval_test(args.query, k=args.results)
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 