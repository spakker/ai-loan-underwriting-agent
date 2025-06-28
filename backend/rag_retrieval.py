import os
import time
import argparse
from typing import List
from langchain.docstore.document import Document
from backend.rag_pipeline import test_retrieval

def run_retrieval_test(query: str, k: int = 5) -> List[Document]:
    """Run a retrieval test with the given query.
    
    Args:
        query (str): The query to test
        k (int, optional): Number of results to return. Defaults to 5.
    
    Returns:
        List[Document]: List of retrieved documents
    """
    try:
        start_time = time.time()
        results = test_retrieval(query, k=k)
        return results
        
    except Exception as e:
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
        raise

if __name__ == "__main__":
    main() 