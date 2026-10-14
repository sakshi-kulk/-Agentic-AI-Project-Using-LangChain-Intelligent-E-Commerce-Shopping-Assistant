"""FAQ retrieval via LangChain/Chroma when configured, with a local fallback."""

import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from database import ROOT_DIR


FAQ_PATH = ROOT_DIR / "data" / "faqs" / "faq_laptop.txt"
load_dotenv(ROOT_DIR / ".env")


@lru_cache(maxsize=2)
def _get_retrieval_chain(persist_directory: str):
    from langchain_classic.chains import RetrievalQA
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import TextLoader
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    embeddings = OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    vector_store = Chroma(
        collection_name="laptop_faqs",
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )
    if not vector_store.get().get("ids"):
        documents = TextLoader(str(FAQ_PATH), encoding="utf-8").load()
        chunks = RecursiveCharacterTextSplitter(
            chunk_size=700, chunk_overlap=100
        ).split_documents(documents)
        vector_store.add_documents(chunks)
    return RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0),
        retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=False,
    )


def _local_faq_answer(question: str, product: dict | None = None) -> str:
    text = FAQ_PATH.read_text(encoding="utf-8")
    query_terms = {
        token.casefold()
        for token in re.findall(r"[a-zA-Z]{3,}", question)
        if token.casefold() not in {"does", "this", "that", "with", "what", "about", "the"}
    }
    sections = [section.strip() for section in text.split("\n\n") if section.strip()]
    scored = sorted(
        ((sum(term in section.casefold() for term in query_terms), section) for section in sections),
        reverse=True,
    )
    excerpts = [section for score, section in scored if score > 0]
    answer = " ".join(excerpts) if excerpts else (
        "The local FAQ does not contain a specific answer. Check the manufacturer's product page."
    )
    if product:
        answer = f"For {product['product_name']}: {answer}"
    return answer


def answer_product_faq(
    question: str,
    product: dict | None = None,
    persist_directory: str | Path | None = None,
    use_llm: bool = True,
) -> str:
    if not question.strip():
        raise ValueError("FAQ question cannot be empty.")
    if use_llm and os.getenv("OPENAI_API_KEY"):
        try:
            location = persist_directory or os.getenv(
                "CHROMA_PERSIST_DIRECTORY", str(ROOT_DIR / "data" / "chroma_db")
            )
            result = _get_retrieval_chain(str(location)).invoke({"query": question})
            answer = str(result.get("result", "")).strip()
            if answer:
                return f"For {product['product_name']}: {answer}" if product else answer
        except Exception:
            # A provider outage, missing optional dependency, or embedding error must not
            # prevent catalog search and recommendations from completing.
            pass
    return _local_faq_answer(question, product)