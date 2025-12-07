"""
RAG Service for semantic search over receipts and knowledge base.
Uses sentence-transformers for generating embeddings and caching them.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
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
        if self.initialized:
            return

        logger.info("Initializing RAG Service...")
        try:
            # Load model - localized for Polish if possible, otherwise multilingual
            # 'paraphrase-multilingual-MiniLM-L12-v2' is good for multi-language
            self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self.initialized = True
            logger.info("RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            self.initialized = False

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text."""
        if not self.initialized:
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
        Note: In a production env, use a vector DB (Chroma, Qdrant).
        For this MVP/Local version, checking receipt text content + simple keyword match
        enhanced with basic semantic understanding if we implement vector storage.

        For now, implementing advanced text search as placeholder for full vector search.
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
