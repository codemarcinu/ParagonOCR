#!/usr/bin/env python3
"""
Import receipts from an external directory (e.g., Obsidian vault) into the ParagonOCR database.
Usage: python scripts/import_obsidian.py --path ~/obsidian --user-id 1
"""

import os
import sys
import argparse
import asyncio
import hashlib
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Set

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.database import get_db_context
from app.models.receipt import Receipt
from app.models.shop import Shop
from app.models.user import User
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.inventory_service import InventoryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("obsidian_import.log")
    ]
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file to detect duplicates."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def process_file(file_path: Path, user_id: int, dry_run: bool):
    """Process a single receipt file."""
    filename = file_path.name
    logger.info(f"Processing: {filename}")

    if dry_run:
        logger.info(f"[DRY-RUN] Would process {file_path}")
        return

    # Check if file content already exists (optional, could add hash column to DB later)
    # For now, check by source_file name match
    # A robust solution would copy the file to data/uploads with a unique name
    
    # 1. Copy to internal storage to ensure availability
    upload_dir = Path("data/uploads/obsidian_import")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique internal filename
    file_hash = calculate_file_hash(file_path)
    target_filename = f"{file_hash[:8]}_{filename}"
    target_path = upload_dir / target_filename
    
    if not target_path.exists():
        shutil.copy2(file_path, target_path)
    
    with get_db_context() as db:
        # Check if already imported
        existing = db.query(Receipt).filter(Receipt.source_file == target_filename).first()
        if existing:
            logger.info(f"Skipping {filename}: Already imported as {existing.id}")
            return

        # Initialize Services
        ocr_service = OCRService()
        llm_service = LLMService()
        inventory_service = InventoryService()
        
        # Create initial record
        unknown_shop = db.query(Shop).filter(Shop.name == "Przetwarzanie...").first()
        if not unknown_shop:
            unknown_shop = Shop(name="Przetwarzanie...")
            db.add(unknown_shop)
            db.flush()

        receipt = Receipt(
            user_id=user_id,
            shop_id=unknown_shop.id,
            purchase_date=datetime.utcnow().date(),
            total_amount=0.0,
            source_file=target_filename,
            status="processing"
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        
        try:
            # 1. OCR
            logger.info(f"Running OCR on {filename}...")
            with open(target_path, "rb") as f:
                content = f.read()
            raw_text = await ocr_service.extract_text(content, filename)
            
            if not raw_text or len(raw_text.strip()) < 10:
                logger.warning(f"OCR failed or empty text for {filename}")
                receipt.status = "failed"
                db.commit()
                return

            # 2. LLM
            logger.info(f"Running LLM analysis on {filename}...")
            parsed_data = await llm_service.process_receipt(raw_text)
            
            # 3. Save Data
            shop_name = parsed_data.get("shop_name", "Nieznany Sklep")
            shop = db.query(Shop).filter(Shop.name == shop_name).first()
            if not shop:
                shop = Shop(name=shop_name)
                db.add(shop)
                db.flush()
            
            purchase_date = parsed_data.get("date")
            if isinstance(purchase_date, str):
                try:
                    purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
                except ValueError:
                    purchase_date = datetime.utcnow().date()
            if not purchase_date:
                purchase_date = datetime.utcnow().date()

            receipt.shop_id = shop.id
            receipt.purchase_date = purchase_date
            receipt.total_amount = parsed_data.get("total_amount", 0.0)
            receipt.ocr_text = raw_text
            receipt.status = "completed"
            
            # Inventory
            items_data = parsed_data.get("items", [])
            inventory_service.process_receipt_items(db, receipt, items_data)
            
            db.commit()
            logger.info(f"Successfully processed {filename} (ID: {receipt.id})")
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            receipt.status = "error"
            db.commit()

async def main():
    parser = argparse.ArgumentParser(description="Import receipts from directory")
    parser.add_argument("--path", required=True, help="Path to directory containing receipts")
    parser.add_argument("--user-id", type=int, default=1, help="User ID to assign receipts to")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not import")
    
    args = parser.parse_args()
    
    source_dir = Path(args.path).expanduser()
    if not source_dir.exists():
        logger.error(f"Directory not found: {source_dir}")
        return

    logger.info(f"Scanning {source_dir}...")
    
    IGNORED_DIRS = {".git", ".obsidian", "venv", ".venv", "node_modules", "__pycache__"}
    
    files_to_process = []
    for root, dirs, files in os.walk(source_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                files_to_process.append(file_path)
                
    logger.info(f"Found {len(files_to_process)} candidate files.")
    
    for file_path in files_to_process:
        await process_file(file_path, args.user_id, args.dry_run)

if __name__ == "__main__":
    asyncio.run(main())
