import os
import numpy as np
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any

class VectorStore:
    """Quản lý Vector DB (ChromaDB) và BM25 Index để tìm kiếm lai (Hybrid Search)."""
    
    def __init__(self, persist_directory: str = "db/.chroma_db"):
        """Khởi tạo ChromaDB và tự động nạp lại dữ liệu cũ nếu có."""
        os.makedirs("db", exist_ok=True)
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="code_knowledge_graph",
            embedding_function=self.embedding_function
        )

        # --- KHỞI TẠO VÀ NẠP CACHE ---
        existing_data = self.collection.get()
        self.doc_ids = existing_data.get('ids', [])
        self.corpus = existing_data.get('documents', [])
        self.bm25 = None

        # Rebuild lại BM25 ngay khi khởi tạo nếu có dữ liệu cũ
        if self.corpus:
            print(f"[*] Đang nạp {len(self.doc_ids)} tài liệu từ cache vào BM25...")
            tokenized_corpus = [doc.lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print("[+] BM25 đã sẵn sàng.")

    def add_nodes(self, nodes: List[Any]):
        """Nhúng GraphNode mới vào ChromaDB và cập nhật Index BM25."""
        ids = []
        documents = []
        metadatas = []
        seen_ids = set(self.doc_ids) # Tránh trùng với dữ liệu đã có trong cache

        for node in nodes:
            if node.type.value not in ["Class", "Function"]:
                continue
            if node.id in seen_ids:
                continue
                
            seen_ids.add(node.id)
            ids.append(node.id)
            
            doc_content = f"Name: {node.name}\nDocstring: {node.content}\nCode: {node.source_code}"
            documents.append(doc_content)
            
            metadatas.append({
                "name": node.name,
                "type": node.type.value,
                "file_path": node.file_path
            })

        if ids:
            print(f"[*] Đang thêm {len(ids)} node mới vào VectorDB và BM25...")
            # 1. Update ChromaDB
            self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            
            # 2. Update dữ liệu bộ nhớ để BM25 không bị mất
            self.corpus.extend(documents)
            self.doc_ids.extend(ids)
            
            # 3. Rebuild BM25 với tập dữ liệu mới nhất
            tokenized_corpus = [doc.lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print("[+] Hoàn tất cập nhật Hybrid Index.")

    def search_vector(self, query: str, top_k: int = 5) -> List[str]:
        """Tìm kiếm ngữ nghĩa thuần túy."""
        results = self.collection.query(query_texts=[query], n_results=top_k)
        return results['ids'][0] if results['ids'] and results['ids'][0] else []

    def search_bm25(self, query: str, top_k: int = 5) -> List[str]:
        """Tìm kiếm từ khóa chính xác."""
        if not self.bm25:
            return []
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.doc_ids[i] for i in top_idx if scores[i] > 0]