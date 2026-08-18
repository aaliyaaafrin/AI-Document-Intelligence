from sentence_transformers import SentenceTransformer
from src.pdf_processor import extract_text_from_pdf, split_text_into_chunks
import chromadb
from dotenv import load_dotenv
import os
from google import genai
load_dotenv()
api_key=os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=api_key)
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(name="documents")
pdf_path = "documents/sample.pdf"
text= extract_text_from_pdf(pdf_path)
chunks= split_text_into_chunks(text)
embeddings = model.encode(chunks)
collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings.tolist()
)
query= input("\nAsk a question about the document: ")
query_embedding=model.encode(query).tolist()
results=collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)
retrieved_chunks = results["documents"][0]
context = "\n\n".join(retrieved_chunks)
print(query)

response = gemini_client.models.generate_content(
    model="gemini-3.6-flash",
    contents=f"""
You are a helpful document assistant.

Answer the user's question based on the information in the document context below.

Document context:
{context}

User question:
{query}

Give a clear and simple answer using the information from the context.
If the context does not contain enough information to answer the question, say that the information is not available in the provided document.
"""
)
print("\nAnswer:")
print(response.text)

