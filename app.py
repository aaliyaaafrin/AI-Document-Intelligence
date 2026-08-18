import os

import chromadb
import streamlit as st
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

from src.pdf_processor import extract_text_from_pdf, split_text_into_chunks


# Page Configuration

st.set_page_config(
    page_title="AI Document Intelligence",
    layout="centered"
)

# Initialize models and clients

model=SentenceTransformer("all-MiniLM-L6-v2")

client=chromadb.PersistentClient(path="chroma_db")
collection=client.get_or_create_collection(
    name="documents"
)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=api_key)

# Application Interface

st.title("AI Document Intelligence")
st.markdown("Upload a PDF and ask questions about its contents.")

# PDF upload

uploaded_file = st.file_uploader(
    "Choose a PDF document",
    type=["pdf"],
    help="Upload a PDF to ask questions about its contents."
)

if uploaded_file is not None:
    st.info(f"Selected file: {uploaded_file.name}")
    os.makedirs("documents", exist_ok=True)
    pdf_path = "documents/uploaded.pdf"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("PDF uploaded successfully!")

# Process PDF

    with st.spinner("Processing your PDF..."):
        text = extract_text_from_pdf(pdf_path)
        chunks = split_text_into_chunks(text)

        embeddings = model.encode(chunks)

        # Remove previous document from ChromaDB

        existing_data = collection.get()
        if existing_data["ids"]:
            collection.delete(ids=existing_data["ids"])

        # Store new document 
        # chunks and embeddings

        collection.add(
            ids=[f"Chunk_{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings.tolist()
        )
    st.success(f"PDF processed successfully! Created {len(chunks)} chunks.") 

# Question section

    st.subheader("Ask a Question")
    question = st.text_input(
        "What would you like to know about this document?"
    )

    if st.button("Ask"):
        if question:

            # convert question into embedding

            query_embedding = model.encode(question).tolist()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results = 5
            )

            # get retrieved chunks

            retrieved_chunks = results["documents"][0]

            #combine chunks into context 

            context = "\n\n".join(retrieved_chunks)

            # generate answer using Gemini

            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=f"""
    You are a helpful document assistant.
    
    Answer the user's question based on the information in the document context below.
    Document context:
    {context}
    User question:
    {question}
    Give a clear and simple answer using the information from the context.
    If the context does not contain enough information to answer the question, say that the information is not available in the provided document.
    """
                )

                # Display Answer

                st.subheader("Answer")
                st.info(response.text)

                #Display retrieved chunks

                with st.expander("View retrieved document chunks"):
                    for i, chunk in enumerate(retrieved_chunks):
                        st.write(f"**Chunk {i + 1}**")
                        st.write(chunk)

            except Exception as e:
                st.error(f"Unable to generate an answer: {e}")
    
        else:
            st.warning("Please enter a question.")