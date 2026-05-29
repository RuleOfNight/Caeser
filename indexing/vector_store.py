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


        # Query: "parse abstract syntax tree"
    # Bước 1: Nhúng query thành vector (384 chiều)
    # Query vector = [0.12, -0.45, 0.78, ..., 0.33]

    # Bước 2: So sánh với tất cả vectors của documents
    # Doc 1 vector = [0.11, -0.43, 0.80, ..., 0.35]  ← cosine similarity = 0.98 ✓ Cao nhất
    # Doc 2 vector = [0.50, 0.20, -0.30, ..., 0.10]  ← cosine similarity = 0.45
    # Doc 3 vector = [0.01, -0.02, 0.03, ..., 0.02]  ← cosine similarity = 0.92

    # Top-1 result: Doc 1 (ID: "class:extraction/extractor.py::CodeKnowledgeExtractor")
    def search_vector(self, query: str, top_k: int = 5) -> List[str]:
        """Tìm kiếm ngữ nghĩa thuần túy."""
        
        # ===== DÒNG 1: NHÚNG QUERY THÀNH VECTOR =====
        results = self.collection.query(query_texts=[query], n_results=top_k)
        #         ↑
        #         ChromaDB nhận câu truy vấn (query) → chuyển thành VECTOR (embedding)
        #         bằng model all-MiniLM-L6-v2 (384 chiều)
        #         Sau đó so sánh VECTOR này với tất cả VECTOR của documents đã lưu
        #         Chọn top_k documents **gần nhất** theo độ tương đồng (cosine similarity)
        
        # ===== DÒNG 2: TRẢ VỀ DANH SÁCH ID =====
        return results['ids'][0] if results['ids'] and results['ids'][0] else []
        #      ↑
        #      results là dict có key 'ids'
        #      results['ids'] là list chứa [[id1, id2, id3, ...]]  (2D array)
        #      results['ids'][0] lấy phần tử đầu tiên → [id1, id2, id3, ...]
        #      Trả về danh sách ID của documents "gần nhất" về NGỮ NGHĨA


    # Query: "parse ast code"
    # Tokenized: ["parse", "ast", "code"]

    # Bước 1: Duyệt tất cả documents
    #    Doc 0: "Name: CodeKnowledgeExtractor\nDocstring: ...\nCode: parse AST extract..."
    #            → Chứa từ "parse" (2x), "ast" (1x), "code" (1x)
    #            → BM25 score = 3.2

    #    Doc 1: "Name: Parser\nDocstring: ...\nCode: tokenize..."
    #            → Chứa từ "ast" (0x), "code" (0x), "parse" (0x)
    #            → BM25 score = 0

    #    Doc 2: "Name: extract_code_info\nDocstring: ...\nCode: ..."
    #            → Chứa từ "code" (2x), nhưng "parse" (0x), "ast" (0x)
    #            → BM25 score = 0.8

    # Bước 2: Xếp hạng từ cao → thấp
    #    1. Doc 0: 3.2 ← TỪ KHÓA MATCH NHẤT
    #    2. Doc 2: 0.8
    #    3. Các doc khác: 0 (không match)

    # Top-1 result: Doc 0
    def search_bm25(self, query: str, top_k: int = 5) -> List[str]:
        """Tìm kiếm từ khóa chính xác."""
        
        # ===== DÒNG 1: KIỂM TRA BM25 CÓ TỒN TẠI =====
        if not self.bm25:
            return []
        #  ↑
        #  Nếu chưa khởi tạo BM25 index → trả về danh sách rỗng
        
        # ===== DÒNG 2: TIA HÓA QUERY THÀNH CÁC TỪ =====
        tokenized_query = query.lower().split()
        #                  ↑
        #                  Chuyển query thành CÁC TỪ RIÊNG LẺ
        #                  Ví dụ: "parse AST code" → ["parse", "ast", "code"]
        #                  (.lower() đổi thành chữ thường để so sánh)
        
        # ===== DÒNG 3: TÍNH ĐIỂM BM25 CHO MỖI DOCUMENT =====
        scores = self.bm25.get_scores(tokenized_query)
        #        ↑
        #        BM25 là thuật toán xếp hạng TỪ KHÓA
        #        Nó tính: "Mỗi document chứa bao nhiêu từ từ query, và từ đó quan trọng không?"
        #        Kết quả: scores = [3.2, 1.5, 0.8, 2.1, ...]
        #                           ↑ doc 0 có điểm 3.2 (chứa "parse" 2 lần, "code" 1 lần)
        #                           ↑ doc 1 có điểm 1.5 (chứa "ast" 1 lần)
        
        # ===== DÒNG 4: TÌM CHỈ SỐ CỦA TOP-K ĐỒ THỊ CAO NHẤT =====
        top_idx = np.argsort(scores)[::-1][:top_k]
        #         ↑                  ↑      ↑
        #         np.argsort: xếp hạng scores từ cao → thấp
        #         [::-1]: đảo ngược (lấy cao nhất trước)
        #         [:top_k]: chỉ lấy top_k phần tử đầu tiên
        #
        #         Ví dụ: scores = [3.2, 1.5, 0.8, 2.1, 0.3]
        #                np.argsort(scores) = [4, 2, 1, 3, 0]  (indices sắp xếp từ thấp→cao)
        #                [::-1] = [0, 3, 1, 2, 4]  (đảo để cao→thấp)
        #                [:2] = [0, 3]  (lấy top 2)
        
        # ===== DÒNG 5: LẤY ID TỪNG DOCUMENT =====
        return [self.doc_ids[i] for i in top_idx if scores[i] > 0]
        #      ↑
        #      Duyệt qua từng index trong top_idx
        #      Lấy self.doc_ids[i] là ID của document thứ i
        #      Điều kiện: chỉ lấy nếu scores[i] > 0 (có ít nhất 1 từ match)
        #      
        #      Kết quả: ["func:app/main.py::run", "class:extraction/extractor.py::Parser", ...]