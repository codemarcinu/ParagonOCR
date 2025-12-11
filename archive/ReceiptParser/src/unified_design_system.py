"""
Unified Design System for ParagonOCR 2.0

This module provides a centralized design system with consistent colors,
spacing, fonts, and icons for the entire application.

Author: ParagonOCR Team
Version: 2.0
"""

from typing import Final


class AppColors:
    """
    Unified color palette for the application.
    
    Provides consistent colors for UI elements, status indicators,
    and theme support (light/dark mode).
    
    Attributes:
        PRIMARY: Primary brand color (blue)
        SUCCESS: Success/positive action color (green)
        WARNING: Warning/caution color (orange)
        ERROR: Error/negative action color (red)
        INFO: Informational color (blue)
        EXPIRED: Color for expired products (red)
        EXPIRING_SOON: Color for products expiring soon (orange)
        OK: Color for OK status (green)
        UNKNOWN: Color for unknown status (gray)
        BG_LIGHT: Light mode background color
        BG_DARK: Dark mode background color
        SURFACE_LIGHT: Light mode surface color
        SURFACE_DARK: Dark mode surface color
        BORDER_LIGHT: Light mode border color
        BORDER_DARK: Dark mode border color
        CHAT_BOT: Light blue color for bot messages
        CHAT_USER: Light green color for user messages
    """
    
    # Primary colors
    PRIMARY: Final[str] = "#1f538d"
    SUCCESS: Final[str] = "#2d8659"
    WARNING: Final[str] = "#d97706"
    ERROR: Final[str] = "#dc2626"
    INFO: Final[str] = "#2563eb"
    
    # Status colors
    EXPIRED: Final[str] = "#dc2626"
    EXPIRING_SOON: Final[str] = "#d97706"
    OK: Final[str] = "#2d8659"
    UNKNOWN: Final[str] = "#6b7280"
    
    # Background colors
    BG_LIGHT: Final[str] = "#f3f4f6"
    BG_DARK: Final[str] = "#1a1a1a"
    
    # Surface colors
    SURFACE_LIGHT: Final[str] = "#ffffff"
    SURFACE_DARK: Final[str] = "#2a2a2a"
    
    # Border colors
    BORDER_LIGHT: Final[str] = "#e5e7eb"
    BORDER_DARK: Final[str] = "#404040"
    
    # Chat colors
    CHAT_BOT: Final[str] = "#e0f2fe"  # Light blue for bot messages
    CHAT_USER: Final[str] = "#f0fdf4"  # Light green for user messages
    
    # Row colors for alternating rows in tables/lists
    ROW_EVEN: Final[str] = "#2a2a2a"  # Even row color (dark mode)
    ROW_ODD: Final[str] = "#333333"  # Odd row color (dark mode)
    ROW_EVEN_LIGHT: Final[str] = "#ffffff"  # Even row color (light mode)
    ROW_ODD_LIGHT: Final[str] = "#f9fafb"  # Odd row color (light mode)
    
    # Primary color variants
    PRIMARY_LIGHT: Final[str] = "#3b82f6"
    PRIMARY_DARK: Final[str] = "#1e40af"
    
    # Success color variants
    SUCCESS_LIGHT: Final[str] = "#22c55e"
    SUCCESS_DARK: Final[str] = "#15803d"
    
    # Warning color variants
    WARNING_LIGHT: Final[str] = "#f59e0b"
    WARNING_DARK: Final[str] = "#b45309"
    
    # Error color variants
    ERROR_LIGHT: Final[str] = "#ef4444"
    ERROR_DARK: Final[str] = "#b91c1c"
    
    # Info color variants
    INFO_LIGHT: Final[str] = "#0ea5e9"
    INFO_DARK: Final[str] = "#0369a1"
    
    # Product status colors
    PRODUCT_EXPIRED: Final[str] = "#dc2626"
    PRODUCT_EXPIRING_SOON: Final[str] = "#f97316"
    PRODUCT_EXPIRING_MEDIUM: Final[str] = "#eab308"
    PRODUCT_OK: Final[str] = "#22c55e"
    PRODUCT_UNKNOWN: Final[str] = "#6b7280"
    
    # Background colors (extended)
    BG_PRIMARY: Final[str] = "#0f172a"
    BG_SECONDARY: Final[str] = "#1e293b"
    BG_TERTIARY: Final[str] = "#334155"
    BG_PRIMARY_LIGHT: Final[str] = "#f8fafc"
    BG_SECONDARY_LIGHT: Final[str] = "#f1f5f9"
    BG_TERTIARY_LIGHT: Final[str] = "#e2e8f0"
    
    # Text colors
    TEXT_PRIMARY: Final[str] = "#f8fafc"
    TEXT_SECONDARY: Final[str] = "#cbd5e1"
    TEXT_TERTIARY: Final[str] = "#94a3b8"
    TEXT_PRIMARY_LIGHT: Final[str] = "#0f172a"
    TEXT_SECONDARY_LIGHT: Final[str] = "#475569"
    TEXT_TERTIARY_LIGHT: Final[str] = "#64748b"
    
    # Other colors
    BORDER_LIGHT_LIGHT: Final[str] = "#cbd5e1"
    HIGHLIGHT: Final[str] = "#fbbf24"
    DISABLED: Final[str] = "#475569"
    
    @staticmethod
    def get_status_color(days_until_expiry: int) -> str:
        """
        Returns color based on days until expiry.
        
        Args:
            days_until_expiry: Number of days until expiry (negative = expired)
            
        Returns:
            Color hex code for the status
        """
        if days_until_expiry < 0:
            return AppColors.PRODUCT_EXPIRED
        elif days_until_expiry <= 3:
            return AppColors.PRODUCT_EXPIRING_SOON
        elif days_until_expiry <= 7:
            return AppColors.PRODUCT_EXPIRING_MEDIUM
        elif days_until_expiry > 7:
            return AppColors.PRODUCT_OK
        else:
            return AppColors.PRODUCT_UNKNOWN


class AppSpacing:
    """
    Unified spacing system for consistent padding and margins.
    
    Provides predefined spacing values to maintain visual consistency
    across all UI components.
    
    Attributes:
        XS: Extra small spacing (4px)
        SM: Small spacing (8px)
        MD: Medium spacing (12px)
        LG: Large spacing (16px)
        XL: Extra large spacing (20px)
        XXL: 2X large spacing (24px)
        3XL: 3X large spacing (32px)
    """
    
    XS: Final[int] = 4
    SM: Final[int] = 8
    MD: Final[int] = 12
    LG: Final[int] = 16
    XL: Final[int] = 20
    XXL: Final[int] = 24
    XXXL: Final[int] = 32
    
    # Presets for common UI patterns
    BUTTON_PADDING_H: Final[int] = 16  # Horizontal button padding
    BUTTON_PADDING_V: Final[int] = 10  # Vertical button padding
    DIALOG_PADDING: Final[int] = 20  # Dialog padding
    FORM_FIELD_SPACING: Final[int] = 12  # Spacing between form fields
    TABLE_CELL_PADDING_H: Final[int] = 12  # Horizontal table cell padding
    TABLE_CELL_PADDING_V: Final[int] = 8  # Vertical table cell padding
    TABLE_ROW_HEIGHT: Final[int] = 32  # Table row height


class AppFont:
    """
    Unified font system for consistent typography.
    
    Provides font sizes, weights, and family definitions
    for consistent text rendering across the application.
    
    Attributes:
        SIZE_XS: Extra small font size (11px)
        SIZE_SM: Small font size (12px)
        SIZE_BASE: Base font size (14px)
        SIZE_MD: Medium font size (16px)
        SIZE_LG: Large font size (18px)
        SIZE_XL: Extra large font size (20px)
        SIZE_2XL: 2X large font size (24px)
        WEIGHT_REGULAR: Regular font weight (400)
        WEIGHT_MEDIUM: Medium font weight (500)
        WEIGHT_SEMIBOLD: Semibold font weight (600)
        WEIGHT_BOLD: Bold font weight (700)
        FAMILY_BASE: Base font family tuple
        FAMILY_MONO: Monospace font family tuple
    """
    
    SIZE_XS: Final[int] = 11
    SIZE_SM: Final[int] = 12
    SIZE_BASE: Final[int] = 14
    SIZE_MD: Final[int] = 16
    SIZE_LG: Final[int] = 18
    SIZE_XL: Final[int] = 20
    SIZE_2XL: Final[int] = 24
    
    WEIGHT_REGULAR: Final[int] = 400
    WEIGHT_MEDIUM: Final[int] = 500
    WEIGHT_SEMIBOLD: Final[int] = 600
    WEIGHT_BOLD: Final[int] = 700
    
    FAMILY_BASE: Final[tuple] = ("Segoe UI", "Arial", "sans-serif")
    FAMILY_MONO: Final[tuple] = ("Consolas", "Courier New", "monospace")
    
    # Presets for common text styles
    @staticmethod
    def TITLE_MAIN(size: int = None) -> tuple:
        """Main title font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_2XL, "bold")
    
    @staticmethod
    def TITLE_SECTION(size: int = None) -> tuple:
        """Section title font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_XL, "bold")
    
    @staticmethod
    def BODY(size: int = None) -> tuple:
        """Body text font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_BASE, "normal")
    
    @staticmethod
    def BODY_SMALL(size: int = None) -> tuple:
        """Small body text font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_SM, "normal")
    
    @staticmethod
    def LABEL(size: int = None) -> tuple:
        """Label font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_BASE, "normal")
    
    @staticmethod
    def LABEL_SMALL(size: int = None) -> tuple:
        """Small label font preset"""
        return (AppFont.FAMILY_BASE[0], size or AppFont.SIZE_SM, "normal")


class Icons:
    """
    Unified icon system using emoji icons.
    
    Provides consistent emoji icons for UI elements,
    buttons, and status indicators.
    
    Attributes:
        RECEIPT: Receipt icon
        COOKING: Cooking/kitchen icon
        ADD: Add/plus icon
        CHAT: Chat/message icon
        INVENTORY: Inventory/warehouse icon
        SETTINGS: Settings/gear icon
        REFRESH: Refresh/reload icon
        DELETE: Delete/trash icon
        SAVE: Save icon
        SEARCH: Search icon
        SEND: Send icon
        COPY: Copy icon
        EXPORT: Export icon
        CLEAR: Clear/clean icon
        HISTORY: History icon
        SUCCESS: Success checkmark icon
        ERROR: Error cross icon
        WARNING: Warning icon
        BEAR: Bielik (eagle) AI assistant icon
        MEAL_PLANNER: Meal planner icon
        ANALYTICS: Analytics/statistics icon
        FILE: File/document icon
        SHOP: Shop/store icon
        CATEGORY: Category icon
        PRODUCT: Product/shopping icon
        CALENDAR: Calendar icon
    """
    
    RECEIPT: Final[str] = "📄"
    COOKING: Final[str] = "🍳"
    ADD: Final[str] = "➕"
    CHAT: Final[str] = "💬"
    INVENTORY: Final[str] = "📦"
    SETTINGS: Final[str] = "⚙️"
    REFRESH: Final[str] = "🔄"
    DELETE: Final[str] = "🗑️"
    SAVE: Final[str] = "💾"
    SEARCH: Final[str] = "🔍"
    SEND: Final[str] = "📤"
    COPY: Final[str] = "📋"
    EXPORT: Final[str] = "📊"
    CLEAR: Final[str] = "🧹"
    HISTORY: Final[str] = "📜"
    SUCCESS: Final[str] = "✅"
    ERROR: Final[str] = "❌"
    WARNING: Final[str] = "⚠️"
    BEAR: Final[str] = "🦅"  # Bielik (eagle) icon for AI assistant
    MEAL_PLANNER: Final[str] = "🍽️"  # Meal planner icon
    ANALYTICS: Final[str] = "📈"  # Analytics/statistics icon
    FILE: Final[str] = "📁"  # File/document icon
    SHOP: Final[str] = "🏪"  # Shop/store icon
    CATEGORY: Final[str] = "📂"  # Category icon
    PRODUCT: Final[str] = "🛒"  # Product/shopping icon
    CALENDAR: Final[str] = "📅"  # Calendar icon
    
    # Additional icons for GUI redesign
    REMOVE: Final[str] = "❌"  # Remove icon
    EDIT: Final[str] = "✏️"  # Edit icon
    CANCEL: Final[str] = "🚫"  # Cancel icon
    COOK: Final[str] = "🍳"  # Cook icon (alias for COOKING)
    WASTE: Final[str] = "🗑️"  # Waste icon (alias for DELETE)
    ASSISTANT: Final[str] = "🦅"  # Assistant icon (alias for BEAR)
    EXPAND: Final[str] = "▶️"  # Expand icon
    COLLAPSE: Final[str] = "▼"  # Collapse icon
    INFO: Final[str] = "ℹ️"  # Info icon


class VisualConstants:
    """
    Visual constants for UI components.
    
    Provides standardized dimensions, border radius, and other
    visual constants for consistent UI appearance.
    
    Attributes:
        BUTTON_HEIGHT: Standard button height (40px)
        BUTTON_HEIGHT_SMALL: Small button height (32px)
        BUTTON_HEIGHT_LARGE: Large button height (48px)
        INPUT_HEIGHT: Standard input height (40px)
        INPUT_HEIGHT_SMALL: Small input height (32px)
        BORDER_RADIUS_SM: Small border radius (4px)
        BORDER_RADIUS_MD: Medium border radius (8px)
        BORDER_RADIUS_LG: Large border radius (12px)
        BORDER_WIDTH_THIN: Thin border width (1px)
        BORDER_WIDTH_NORMAL: Normal border width (2px)
        WINDOW_MIN_WIDTH: Minimum window width (1000px)
        WINDOW_MIN_HEIGHT: Minimum window height (700px)
        DIALOG_MIN_WIDTH: Minimum dialog width (600px)
        DIALOG_MIN_HEIGHT: Minimum dialog height (400px)
        REVIEW_DIALOG_WIDTH: Review dialog width (1200px)
        REVIEW_DIALOG_HEIGHT: Review dialog height (800px)
    """
    
    # Button heights
    BUTTON_HEIGHT: Final[int] = 40
    BUTTON_HEIGHT_SMALL: Final[int] = 32
    BUTTON_HEIGHT_LARGE: Final[int] = 48
    
    # Input heights
    INPUT_HEIGHT: Final[int] = 40
    INPUT_HEIGHT_SMALL: Final[int] = 32
    
    # Border radius
    BORDER_RADIUS_SM: Final[int] = 4
    BORDER_RADIUS_MD: Final[int] = 8
    BORDER_RADIUS_LG: Final[int] = 12
    
    # Border width
    BORDER_WIDTH_THIN: Final[int] = 1
    BORDER_WIDTH_NORMAL: Final[int] = 2
    
    # Window dimensions
    WINDOW_MIN_WIDTH: Final[int] = 1000
    WINDOW_MIN_HEIGHT: Final[int] = 700
    
    # Dialog dimensions
    DIALOG_MIN_WIDTH: Final[int] = 600
    DIALOG_MIN_HEIGHT: Final[int] = 400
    REVIEW_DIALOG_WIDTH: Final[int] = 1200
    REVIEW_DIALOG_HEIGHT: Final[int] = 800

