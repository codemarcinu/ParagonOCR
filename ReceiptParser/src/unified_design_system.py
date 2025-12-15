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
    WASTE: Final[str] = "#8b4513"  # Brown for waste/compost
    
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
    CHAT_BOT: Final[tuple] = ("#e0f2fe", "#1e40af")  # (Light, Dark) - Light blue / Dark blue
    CHAT_USER: Final[tuple] = ("#f0fdf4", "#166534")  # (Light, Dark) - Light green / Dark green
    
    # Row colors for alternating rows in tables/lists
    ROW_EVEN: Final[str] = "#2a2a2a"  # Even row color (dark mode)
    ROW_ODD: Final[str] = "#333333"  # Odd row color (dark mode)
    ROW_EVEN_LIGHT: Final[str] = "#ffffff"  # Even row color (light mode)
    ROW_ODD_LIGHT: Final[str] = "#f9fafb"  # Odd row color (light mode)


class AppSpacing:
    """
    Unified spacing system for consistent padding and margins.
    
    Provides predefined spacing values to maintain visual consistency
    across all UI components.
    
    Attributes:
        XS: Extra small spacing (5px)
        SM: Small spacing (10px)
        MD: Medium spacing (15px)
        LG: Large spacing (20px)
        XL: Extra large spacing (30px)
        XXL: Extra extra large spacing (40px)
    """
    
    XS: Final[int] = 5
    SM: Final[int] = 10
    MD: Final[int] = 15
    LG: Final[int] = 20
    XL: Final[int] = 30
    XXL: Final[int] = 40


class AppFont:
    """
    Unified font system for consistent typography.
    
    Provides font sizes, weights, and family definitions
    for consistent text rendering across the application.
    
    Attributes:
        SIZE_XS: Extra small font size (10px)
        SIZE_SM: Small font size (11px)
        SIZE_MD: Medium font size (12px)
        SIZE_LG: Large font size (14px)
        SIZE_XL: Extra large font size (16px)
        SIZE_2XL: 2X large font size (18px)
        SIZE_3XL: 3X large font size (20px)
        WEIGHT_NORMAL: Normal font weight (400)
        WEIGHT_MEDIUM: Medium font weight (500)
        WEIGHT_BOLD: Bold font weight (600)
        FAMILY: Font family name (Segoe UI)
    """
    
    SIZE_XS: Final[int] = 10
    SIZE_SM: Final[int] = 11
    SIZE_MD: Final[int] = 12
    SIZE_LG: Final[int] = 14
    SIZE_XL: Final[int] = 16
    SIZE_2XL: Final[int] = 18
    SIZE_3XL: Final[int] = 20
    
    WEIGHT_NORMAL: Final[int] = 400
    WEIGHT_MEDIUM: Final[int] = 500
    WEIGHT_BOLD: Final[int] = 600
    
    FAMILY: Final[str] = "Segoe UI"


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
    STATUS_DOT: Final[str] = "●"  # Circle dot for status indicators


def adjust_color(color: str, amount: int) -> str:
    """
    Brightern or darken a hex color by a given amount.
    
    Args:
        color: Hex color string (e.g. "#1f538d")
        amount: Amount to adjust (-255 to 255). Positive for lighter, negative for darker.
        
    Returns:
        Adjusted hex color string.
    """
    try:
        # Convert hex to RGB
        color = color.lstrip("#")
        rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        # Adjust brightness
        new_rgb = tuple(max(0, min(255, c + amount)) for c in rgb)
        # Convert back to hex
        return "#%02x%02x%02x" % new_rgb
    except Exception:
        return color

