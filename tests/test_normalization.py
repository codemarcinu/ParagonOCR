"""
Unit tests for normalization service.
"""
import pytest
from app.services.normalization import normalize_unit, normalize_product_name, classify_product_category
from app.models.product import Product, ProductAlias
from app.models.category import Category

class TestNormalization:
    
    def test_normalize_unit(self):
        """Test unit normalization logic."""
        # Standard mappings
        assert normalize_unit("szt") == "szt"
        assert normalize_unit("szt.") == "szt"
        assert normalize_unit("st.") == "szt"
        assert normalize_unit("opak") == "szt"
        
        # Case insensitivity
        assert normalize_unit("KG") == "kg"
        assert normalize_unit("Kg.") == "kg"
        
        # No change for unknown
        assert normalize_unit("galon") == "galon"
        
        # None handling
        assert normalize_unit(None) is None

    def test_normalize_product_name_create_new(self, db_session):
        """Test creating a new product from raw name."""
        raw_name = "Unique Product XYZ"
        
        product, is_new = normalize_product_name(db_session, raw_name)
        
        assert is_new is True
        assert product.normalized_name == raw_name
        assert product.id is not None
        
        # Verify alias creation
        alias = db_session.query(ProductAlias).filter_by(raw_name=raw_name).first()
        assert alias is not None
        assert alias.product_id == product.id

    def test_normalize_product_name_existing_exact(self, db_session):
        """Test retrieving existing product by exact alias match."""
        # Create initial product
        p1, _ = normalize_product_name(db_session, "Coca Cola")
        
        # Try to normalize same string again
        p2, is_new = normalize_product_name(db_session, "Coca Cola")
        
        assert is_new is False
        assert p2.id == p1.id

    def test_classify_product_category_keywords(self, db_session):
        """Test category classification using keywords."""
        # Create products that match keywords in normalization.py
        p_milk = Product(normalized_name="Mleko Łaciate")
        p_bread = Product(normalized_name="Chleb Razowy")
        
        db_session.add(p_milk)
        db_session.add(p_bread)
        db_session.flush()
        
        # Classify
        cat_id_milk = classify_product_category(db_session, p_milk)
        cat_id_bread = classify_product_category(db_session, p_bread)
        
        # Verify
        assert cat_id_milk is not None
        assert cat_id_bread is not None
        
        c_milk = db_session.query(Category).get(cat_id_milk)
        c_bread = db_session.query(Category).get(cat_id_bread)
        
        assert c_milk.name == "Nabiał"
        assert c_bread.name == "Pieczywo"

    def test_classify_product_category_memoization(self, db_session):
        """Test that existing category is reused."""
        p1 = Product(normalized_name="Mleko 1")
        p2 = Product(normalized_name="Mleko 2")
        db_session.add_all([p1, p2])
        db_session.flush()
        
        id1 = classify_product_category(db_session, p1)
        id2 = classify_product_category(db_session, p2)
        
        assert id1 == id2
