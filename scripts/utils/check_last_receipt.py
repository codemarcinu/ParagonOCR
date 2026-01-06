from app.database import get_db_context
from app.models.receipt import Receipt
from sqlalchemy import desc

with get_db_context() as db:
    last_receipt = db.query(Receipt).order_by(desc(Receipt.id)).first()
    if last_receipt:
        print(f"ID: {last_receipt.id}")
        print(f"Shop: {last_receipt.shop.name if last_receipt.shop else 'N/A'}")
        print(f"Date: {last_receipt.purchase_date}")
        print(f"Total: {last_receipt.total_amount}")
        print(f"Status: {last_receipt.status}")
        print("Items:")
        for item in last_receipt.items:
            print(f" - {item.product.name if item.product else item.raw_name}: {item.quantity} {item.unit} x {item.unit_price} = {item.total_price}")
    else:
        print("No receipts found.")
