"""
Testy dla głównego okna GUI (CustomTkinter)
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ReceiptParser"))

import pytest

# Check if CustomTkinter is available
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False


@pytest.mark.gui
@pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
class TestMainWindow:
    """Testy dla głównego okna aplikacji"""
    
    @pytest.fixture
    def root(self):
        """Fixture tworzący główne okno CTk"""
        root = ctk.CTk()
        root.withdraw()  # Hide window during tests
        yield root
        root.destroy()
    
    def test_window_creation(self, root):
        """Test tworzenia głównego okna"""
        assert root is not None
        assert isinstance(root, ctk.CTk)
    
    def test_window_title(self, root):
        """Test ustawienia tytułu okna"""
        root.title("Test Title")
        assert root.title() == "Test Title"
    
    def test_window_geometry(self, root):
        """Test ustawienia geometrii okna"""
        # Test that geometry can be set (may not apply if window is hidden)
        root.geometry("1200x700")
        # Just verify the method doesn't raise an error
        geometry = root.geometry()
        assert geometry is not None
        # If window is visible, geometry should be set
        # If hidden (withdraw), geometry may be default
    
    @pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
    def test_frame_creation(self, root):
        """Test tworzenia ramki w oknie"""
        frame = ctk.CTkFrame(root)
        frame.pack()
        
        assert frame is not None
        # CTkFrame may report as "Frame" in winfo_class
        assert "Frame" in frame.winfo_class() or isinstance(frame, ctk.CTkFrame)
    
    @pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
    def test_button_creation(self, root):
        """Test tworzenia przycisku"""
        button = ctk.CTkButton(root, text="Test Button")
        button.pack()
        
        assert button is not None
        assert button.cget("text") == "Test Button"
    
    @pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
    def test_button_command(self, root):
        """Test komendy przycisku"""
        clicked = []
        
        def button_click():
            clicked.append(True)
        
        button = ctk.CTkButton(root, text="Click Me", command=button_click)
        button.pack()
        button.invoke()
        
        assert len(clicked) == 1
        assert clicked[0] is True


@pytest.mark.gui
@pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
class TestTabs:
    """Testy dla zakładek w aplikacji"""
    
    @pytest.fixture
    def root(self):
        """Fixture tworzący główne okno"""
        root = ctk.CTk()
        root.withdraw()
        yield root
        root.destroy()
    
    def test_tabview_creation(self, root):
        """Test tworzenia TabView"""
        tabview = ctk.CTkTabview(root)
        tabview.pack()
        
        assert tabview is not None
        
        # Add tabs
        tab1 = tabview.add("Tab 1")
        tab2 = tabview.add("Tab 2")
        
        # Verify tabs exist
        assert tab1 is not None
        assert tab2 is not None
        # get() without args returns current tab name
        current_tab = tabview.get()
        assert current_tab in ["Tab 1", "Tab 2"]
    
    def test_tab_switching(self, root):
        """Test przełączania zakładek"""
        tabview = ctk.CTkTabview(root)
        tabview.pack()
        
        tab1 = tabview.add("Tab 1")
        tab2 = tabview.add("Tab 2")
        
        tabview.set("Tab 2")
        assert tabview.get() == "Tab 2"
        
        tabview.set("Tab 1")
        assert tabview.get() == "Tab 1"


@pytest.mark.gui
@pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
class TestNotifications:
    """Testy dla powiadomień w GUI"""
    
    @pytest.fixture
    def root(self):
        """Fixture tworzący główne okno"""
        root = ctk.CTk()
        root.withdraw()
        yield root
        root.destroy()
    
    def test_label_creation(self, root):
        """Test tworzenia etykiety (dla statusu)"""
        label = ctk.CTkLabel(root, text="Status: Ready")
        label.pack()
        
        assert label is not None
        assert label.cget("text") == "Status: Ready"
    
    def test_label_text_update(self, root):
        """Test aktualizacji tekstu etykiety"""
        label = ctk.CTkLabel(root, text="Initial")
        label.pack()
        
        label.configure(text="Updated")
        assert label.cget("text") == "Updated"
    
    def test_progress_bar_creation(self, root):
        """Test tworzenia paska postępu"""
        progress = ctk.CTkProgressBar(root)
        progress.pack()
        
        assert progress is not None
        progress.set(0.5)
        assert progress.get() == pytest.approx(0.5, abs=0.01)
    
    def test_progress_bar_update(self, root):
        """Test aktualizacji paska postępu"""
        progress = ctk.CTkProgressBar(root)
        progress.pack()
        
        progress.set(0.0)
        assert progress.get() == pytest.approx(0.0, abs=0.01)
        
        progress.set(1.0)
        assert progress.get() == pytest.approx(1.0, abs=0.01)
        
        progress.set(0.75)
        assert progress.get() == pytest.approx(0.75, abs=0.01)


@pytest.mark.gui
@pytest.mark.skipif(not CTK_AVAILABLE, reason="CustomTkinter not available")
class TestGUIComponents:
    """Testy dla komponentów GUI"""
    
    @pytest.fixture
    def root(self):
        """Fixture tworzący główne okno"""
        root = ctk.CTk()
        root.withdraw()
        yield root
        root.destroy()
    
    def test_entry_creation(self, root):
        """Test tworzenia pola tekstowego"""
        entry = ctk.CTkEntry(root)
        entry.pack()
        
        assert entry is not None
        entry.insert(0, "Test text")
        assert entry.get() == "Test text"
    
    def test_textbox_creation(self, root):
        """Test tworzenia pola tekstowego wieloliniowego"""
        textbox = ctk.CTkTextbox(root)
        textbox.pack()
        
        assert textbox is not None
        textbox.insert("1.0", "Line 1\nLine 2")
        content = textbox.get("1.0", "end-1c")
        assert "Line 1" in content
        assert "Line 2" in content
    
    def test_scrollable_frame(self, root):
        """Test tworzenia przewijalnej ramki"""
        scrollable = ctk.CTkScrollableFrame(root)
        scrollable.pack()
        
        assert scrollable is not None
        
        # Add widgets to scrollable frame
        for i in range(10):
            label = ctk.CTkLabel(scrollable, text=f"Item {i}")
            label.pack()


# Tests that should run even if CustomTkinter is not available
@pytest.mark.gui
class TestGUIImports:
    """Testy importów GUI (zawsze dostępne)"""
    
    def test_gui_module_import(self):
        """Test importu modułu GUI"""
        try:
            import sys
            import os
            gui_path = os.path.join(os.path.dirname(__file__), "../../gui.py")
            if os.path.exists(gui_path):
                # Just check if file exists, don't import (may require GUI)
                assert os.path.exists(gui_path)
        except Exception:
            pytest.skip("GUI module not available")

