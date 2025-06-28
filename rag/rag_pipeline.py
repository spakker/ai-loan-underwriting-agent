import os, sys, json, time, pathlib, tempfile, shutil, itertools, argparse
from typing import List, Dict
from dotenv import load_dotenv
import weaviate
from langchain_community.vectorstores import WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.document_loaders.image import UnstructuredImageLoader
from langchain.document_loaders.pdf import PyMuPDFLoader
from langchain.docstore.document import Document
from langchain.evaluation import load_evaluator
import pandas as pd
from tqdm import tqdm


# Load environment variables
load_dotenv()
###############################################################################
# 1. Helpers – OCR, loading, chunking
###############################################################################
OCR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}
def ocr_image(path: pathlib.Path) -> str:
    """OCR a single image file with Tesseract."""
    import pytesseract, PIL.Image
    return pytesseract.image_to_string(PIL.Image.open(path))
def load_documents(folder: str) -> List[Document]:
    """Load & OCR a mixed folder of PDFs / images / DOCX files."""
    docs = []
    for fp in pathlib.Path(folder).rglob("*"):
        if fp.is_dir(): continue
        ext = fp.suffix.lower()
        if ext == ".pdf":
            docs.extend(PyPDFLoader(str(fp)).load())
        elif ext in {".docx", ".doc"}:
            docs.extend(Docx2txtLoader(str(fp)).load())
        elif ext in OCR_EXTENSIONS:
            txt = ocr_image(fp)
            docs.append(Document(page_content=txt, metadata={"source": str(fp)}))
    return docs
def chunk_documents(docs: List[Document], chunk_size=400, chunk_overlap=40) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                              chunk_overlap=chunk_overlap,
                                              separators=["\n\n", "\n", " ", ""])
    return splitter.split_documents(docs)
###############################################################################
# 2. Vector DB Initialisation
###############################################################################
def get_weaviate_client() -> weaviate.Client:
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    auth = weaviate.auth.AuthApiKey(api_key) if api_key else None
    return weaviate.Client(url, auth_client_secret=auth)
def get_vector_store(class_name: str = "PolicyChunks") -> WeaviateVectorStore:
    client = get_weaviate_client()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # Create schema if it doesn't exist
    if not client.schema.contains({"class": class_name}):
        client.schema.create({
            "class": class_name,
            "vectorizer": "none",  	# We rely on LangChain to compute vectors
            "properties": [
                {"name": "text", "dataType": ["text"]},
                {"name": "source", "dataType": ["text"]},
                {"name": "page", "dataType": ["int"]},
            ],
            "moduleConfig": {
                "text2vec-openai": { "vectorizeClassName": False },
                "bm25": {},         	# enable BM25 for hybrid search
            }
        })
    return WeaviateVectorStore(
        client=client,
        index_name=class_name,
        text_key="text",
        attributes=["source", "page"],
        embedding=embeddings,
    )
###############################################################################
# 3. Indexing pipeline
###############################################################################
def index_folder(folder: str, class_name="PolicyChunks", alpha=0.5):
    docs = load_documents(folder)
    print(f"Loaded {len(docs)} raw pages")
    chunks = chunk_documents(docs)
    print(f"Split into {len(chunks)} chunks")
    store = get_vector_store(class_name)
    store.add_documents(chunks)
    print("  Finished indexing")
###############################################################################
# 4. Query pipeline
###############################################################################
def build_rag_chain(class_name="PolicyChunks", alpha=0.5, k=5):
    store = get_vector_store(class_name)
    retriever = store.as_retriever(search_type="hybrid", search_kwargs={"k": k, "alpha": alpha})
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    return RetrievalQA.from_chain_type(
        llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={
            "prompt": RetrievalQA.get_default_prompt().copy().partial(context="{context}"),
            # Add simple guard‑rail: force answer to rely on context
            "output_key": "result",
        }
    )
def answer_question(query: str, chain):
    t0 = time.perf_counter()
    resp = chain({"query": query})
    latency = time.perf_counter() - t0
    answer = resp["result"]
    sources = [{
        "source": d.metadata.get("source"),
        "page": d.metadata.get("page"),
        "chunk": d.page_content[:200]
    } for d in resp["source_documents"]]
    return answer, sources, latency
###############################################################################
# 5. Evaluation harness
###############################################################################
def evaluate(gold_csv: str, class_name="PolicyChunks", alpha=0.5, k=5):
    df = pd.read_csv(gold_csv)  # columns: query, gold_answer
    chain = build_rag_chain(class_name, alpha, k)
    precision_hits, total = 0, 0
    halluc_hits, correct_hits = 0, 0
    rows = []
    llm_judge = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)  # cheaper eval
    truthful_eval = load_evaluator("cot_qa", llm=llm_judge)
    for _, row in tqdm(df.iterrows(), total=len(df)):
        ans, srcs, lat = answer_question(row["query"], chain)
        # retrieval precision @k
        is_relevant = any(row["gold_answer"].lower() in s["chunk"].lower() for s in srcs)
        precision_hits += int(is_relevant)
        total += 1
        # generation correctness judged by LLM
        result = truthful_eval.evaluate(
            input=row["query"],
            prediction=ans,
            reference=row["gold_answer"]
        )
        halluc_hits += int(result["soap"] == "No")   # "No hallucination"
        correct_hits += int(result["reasoning"] == "Correct")
        rows.append({
            "query": row["query"],
            "answer": ans,
            "latency": round(lat, 2),
            "retrieval_hit": is_relevant,
            "hallucination_free": result["soap"] == "No",
            "answer_correct": result["reasoning"] == "Correct"
        })
    report = pd.DataFrame(rows)
    print("\n=====  METRICS  =====")
    print(f"Context Precision@{k}: {precision_hits/total:.2%}")
    print(f"Hallucination‑free rate: {halluc_hits/total:.2%}")
    print(f"Answer correctness rate: {correct_hits/total:.2%}")
    print(f"Median latency (s): {report['latency'].median():.2f}")
    report.to_csv("eval_report.csv", index=False)
    print("Detailed row‑level results saved to eval_report.csv")
###############################################################################
# 6. CLI dispatcher
###############################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub_index = sub.add_parser("index")
    sub_index.add_argument("folder")
    sub_query = sub.add_parser("query")
    sub_query.add_argument("question")
    sub_eval = sub.add_parser("eval")
    sub_eval.add_argument("gold_csv")
    args = parser.parse_args()
    if args.cmd == "index":
        index_folder(args.folder)
    elif args.cmd == "query":
        chain = build_rag_chain()
        ans, srcs, lat = answer_question(args.question, chain)
        print("\n  ANSWER:", ans)
        print("  Latency:", round(lat, 2), "s")
        print("  Sources:")
        for s in srcs: print("  –", s)
    elif args.cmd == "eval":
        evaluate(args.gold_csv)
    else:
        parser.print_help()