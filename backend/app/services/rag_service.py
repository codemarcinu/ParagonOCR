"""
RAG Service for semantic search over receipts and knowledge base.
Uses sentence-transformers for generating embeddings and caching them.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
# [LAZY LOAD] Removed top-level import of numpy and sentence_transformers
# import numpy as np
# from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.receipt import Receipt, ReceiptItem
from app.models.product import Product
from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        self.model = None
        # Don't load on init, load on first use or explicitly
        pass

    def _ensure_model_loaded(self):
        """Lazy load the model only when needed."""
        if self.initialized and self.model is not None:
            return

        logger.info("Lazy loading RAG Model (SentenceTransformer)...")
        try:
            # [LAZY LOAD] Import here
            from sentence_transformers import SentenceTransformer
            
            # Load model - localized for Polish if possible, otherwise multilingual
            self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self.initialized = True
            logger.info("RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            self.initialized = False
            self.model = None

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text."""
        self._ensure_model_loaded()
        
        if not self.initialized or self.model is None:
            return []

        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def search_receipts(
        self, query: str, db: Session, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over receipts.
        """
        # TODO: Implement vector storage for receipts
        # Current implementation: Improved SQL search

        results = []

        # Search in receipt items (product names)
        items = (
            db.query(ReceiptItem)
            .filter(ReceiptItem.raw_name.ilike(f"%{query}%"))
            .limit(limit * 2)
            .all()
        )

        seen_receipts = set()

        for item in items:
            if item.receipt_id in seen_receipts:
                continue

            receipt = item.receipt
            if not receipt:
                continue

            results.append(
                {
                    "type": "receipt_item",
                    "score": 0.9,  # Placeholder score
                    "content": f"Found '{item.raw_name}' in receipt from {receipt.shop.name if receipt.shop else 'Unknown'}",
                    "metadata": {
                        "receipt_id": receipt.id,
                        "date": receipt.purchase_date,
                        "price": item.total_price,
                    },
                }
            )
            seen_receipts.add(receipt.receipt_id)

        # 2. Search in Shops (Receipts)
        # Find receipts where shop name matches query
        from app.models.shop import Shop
        
        receipts_by_shop = (
            db.query(Receipt)
            .join(Shop)
            .filter(Shop.name.ilike(f"%{query}%"))
            .order_by(Receipt.purchase_date.desc())
            .limit(limit)
            .all()
        )
        
        for receipt in receipts_by_shop:
             if receipt.id in seen_receipts: continue
             results.append({
                 "type": "receipt",
                 "score": 0.85,
                 "content": f"Receipt from {receipt.shop.name} on {receipt.purchase_date}. Total: {receipt.total_amount}",
                 "metadata": {
                        "receipt_id": receipt.id,
                        "date": receipt.purchase_date,
                        "price": receipt.total_amount,
                 }
             })
             seen_receipts.add(receipt.id)

        return results[:limit]

    def get_context_for_chat(self, query: str, db: Session) -> str:
        """
        Retrieve context relevant to the query to feed into LLM.
        """
        search_results = self.search_receipts(query, db)

        if not search_results:
            return "No specific receipt data found for this query."

        context_parts = ["Relevant receipt information:"]
        for res in search_results:
            context_parts.append(f"- {res['content']} ({res['metadata']['date']})")

        return "\n".join(context_parts)


rag_service = RAGService()
