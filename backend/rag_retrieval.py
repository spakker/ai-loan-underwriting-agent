import os
import time
import argparse
from typing import List
from langchain.docstore.document import Document
from backend.rag_pipeline import get_weaviate_client, WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings

def run_retrieval_test(query: str, k: int = 5) -> List[Document]:
    """Run a retrieval test with the given query.
    
    Args:
        query (str): The query to test
        k (int, optional): Number of results to return. Defaults to 5.
    
    Returns:
        List[Document]: List of retrieved documents
    """
    client = None
    try:
        start_time = time.time()
        client = get_weaviate_client()
        
        vector_store = WeaviateVectorStore(
            client=client,
            index_name="PolicyChunks",
            text_key="text",
            embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
            attributes=["source", "page"]
        )
        
        results = vector_store.similarity_search(query, k=k)
        print(f"\nQuery: {query}")
        print(f"Found {len(results)} results in {time.time() - start_time:.2f} seconds\n")
        
        for i, doc in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Source: {doc.metadata.get('source', 'N/A')}")
            print(f"Page: {doc.metadata.get('page', 'N/A')}")
            print(f"Content: {doc.page_content[:500]}...")
        
        return results
        
    except Exception as e:
        print(f"Error during retrieval: {str(e)}")
        raise
    finally:
        if client:
            client.close()

def main():
    parser = argparse.ArgumentParser(description='Test RAG retrieval with a query')
    parser.add_argument('--query', type=str, default="What is the minimum credit score for a fixed‑rate loan?",
                      help='Query to test retrieval')
    parser.add_argument('--results', type=int, default=5,
                      help='Number of results to return (default: 5)')
    args = parser.parse_args()
    
    try:
        run_retrieval_test(args.query, k=args.results)
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 