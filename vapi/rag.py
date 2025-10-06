
import os
import json
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


class RAGEngine:
    def __init__(
        self,
        docs_path="Rules.txt",
        faiss_path="vector_store/faiss_index",
        apartment_path="vector_store/apartment_index",
        apartment_json_path="data.json"
    ):
        self.docs_path = docs_path
        self.faiss_path = faiss_path
        self.apartment_faiss_path = apartment_path
        self.apartment_json_path = apartment_json_path
        self.model_name = "BAAI/bge-base-en"
        
        self.embedding_model = HuggingFaceEmbeddings(model_name=self.model_name)

        # Load or build rules index
        if self._faiss_index_exists(self.faiss_path):
            print("Loading existing Rules FAISS index...")
            self.db = FAISS.load_local(
                self.faiss_path,
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
        else:
            print("No existing Rules FAISS index found. Building from docs...")
            self.db = self._build_vector_store()
            self.db.save_local(self.faiss_path)
            print("Rules FAISS index saved.")

        # Load or build apartment index
        if self._faiss_index_exists(self.apartment_faiss_path):
            print("Loading existing Apartment FAISS index...")
            self.apartment_db = FAISS.load_local(
                self.apartment_faiss_path,
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
        else:
            print("No existing Apartment FAISS index found. Building from JSON...")
            self.apartment_db = self._build_apartment_index(self.apartment_json_path)
            self.apartment_db.save_local(self.apartment_faiss_path)
            print("Apartment FAISS index saved.")

    def _faiss_index_exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(path, "index.faiss")) and \
           os.path.exists(os.path.join(path, "index.pkl"))

    def _build_vector_store(self):
        if not os.path.exists(self.docs_path):
            raise FileNotFoundError(f"File '{self.docs_path}' not found.")

        loader = TextLoader(self.docs_path)
        documents = loader.load()

        splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        return FAISS.from_documents(chunks, self.embedding_model)

    def query(self, question: str, k: int = 3) -> str:
        results = self.db.similarity_search(question, k=k)
        context = "\n".join([doc.page_content for doc in results])
        return f"Here are the most relevant parts:\n\n{context}"

    def listing_to_text(self, listing: dict) -> str:
        return (
            f"{listing['bedrooms']} bed, {listing['bathrooms']} bath "
            f"{listing['property_type']} in {listing['address']}, "
            f"listed at ${listing['price']} with {listing['square_feet']} sqft. "
            f"Features include: {', '.join(listing.get('features', []))}."
        )

    def _build_apartment_index(self, json_path: str):
        print("Building apartment semantic index...")
        listings = []

        with open(json_path, "r") as f:
            data_list = json.load(f)
            for data in data_list:
                text = self.listing_to_text(data)
                listings.append(Document(page_content=text, metadata={"source": data}))

        return FAISS.from_documents(listings, self.embedding_model)

    def search_apartments(self, query: str, k: int = 5):
        if not self.apartment_db:
            raise RuntimeError("Apartment FAISS index not loaded.")

        results = self.apartment_db.similarity_search(query, k=k)
        return [res.metadata["source"] for res in results]
