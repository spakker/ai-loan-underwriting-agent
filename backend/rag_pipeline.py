import os
from typing import List, Optional
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
import PyPDF2

def load_pdf_documents(pdf_paths: List[str]) -> List[Document]:
    """Load PDF documents and convert them to text."""
    documents = []
    for pdf_path in pdf_paths:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            documents.append(Document(page_content=text, metadata={"source": pdf_path}))
    return documents

def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    return text_splitter.split_documents(documents)

def create_vector_store(documents: List[Document], persist_directory: str) -> Chroma:
    """Create and persist a vector store from documents."""
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    vectorstore.persist()
    return vectorstore

def test_retrieval(query: str, k: int = 5, persist_directory: Optional[str] = None) -> List[Document]:
    """Test document retrieval with a query."""
    if persist_directory is None:
        persist_directory = os.path.join(os.path.dirname(__file__), ".cache")
    
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    
    return vectorstore.similarity_search(query, k=k)

def main():
    # Example usage
    pdf_paths = ["policy_docs/Selling-Guide_06-4-2025_Highlighted (2).pdf"]
    persist_directory = ".cache"
    
    # Load and process documents
    documents = load_pdf_documents(pdf_paths)
    chunks = split_documents(documents)
    vectorstore = create_vector_store(chunks, persist_directory)
    
    # Test retrieval
    query = "What are the requirements for mortgage insurance?"
    results = test_retrieval(query)
    
    for i, doc in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(doc.page_content[:200] + "...")

if __name__ == "__main__":
    main() 