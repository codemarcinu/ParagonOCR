"""
Modern GUI Components for ParagonOCR 2.0

This module provides modern, reusable UI components built on top of CustomTkinter
that follow the unified design system.

Author: ParagonOCR Team
Version: 2.0
"""

import customtkinter as ctk
from src.unified_design_system import (
    AppColors,
    AppFont,
    AppSpacing,
    Icons,
    VisualConstants,
)


class ModernButton(ctk.CTkButton):
    """
    Modern button component with design system integration.
    
    Provides pre-configured button styles with variants and sizes.
    
    Args:
        variant: Button style variant ('primary', 'secondary', 'success', 'warning', 'error', 'ghost')
        size: Button size ('sm', 'md', 'lg')
        **kwargs: Additional arguments passed to CTkButton
    """
    
    def __init__(
        self,
        master,
        variant: str = "primary",
        size: str = "md",
        **kwargs
    ):
        # Get colors based on variant
        variant_colors = {
            "primary": (AppColors.PRIMARY, AppColors.PRIMARY_DARK),
            "secondary": (AppColors.BG_SECONDARY, AppColors.BG_TERTIARY),
            "success": (AppColors.SUCCESS, AppColors.SUCCESS_DARK),
            "warning": (AppColors.WARNING, AppColors.WARNING_DARK),
            "error": (AppColors.ERROR, AppColors.ERROR_DARK),
            "ghost": ("transparent", AppColors.BG_SECONDARY),
        }
        
        fg_color, hover_color = variant_colors.get(variant, variant_colors["primary"])
        
        # Get height based on size
        size_heights = {
            "sm": VisualConstants.BUTTON_HEIGHT_SMALL,
            "md": VisualConstants.BUTTON_HEIGHT,
            "lg": VisualConstants.BUTTON_HEIGHT_LARGE,
        }
        height = size_heights.get(size, VisualConstants.BUTTON_HEIGHT)
        
        # Get font size based on size
        size_fonts = {
            "sm": AppFont.SIZE_SM,
            "md": AppFont.SIZE_BASE,
            "lg": AppFont.SIZE_MD,
        }
        font_size = size_fonts.get(size, AppFont.SIZE_BASE)
        
        # Set default values
        defaults = {
            "fg_color": fg_color,
            "hover_color": hover_color,
            "height": height,
            "font": (AppFont.FAMILY_BASE[0], font_size),
            "corner_radius": VisualConstants.BORDER_RADIUS_MD,
            "border_width": 0,
        }
        
        # Merge defaults with user kwargs (user kwargs take precedence)
        final_kwargs = {**defaults, **kwargs}
        
        super().__init__(master, **final_kwargs)


class ModernLabel(ctk.CTkLabel):
    """
    Modern label component with design system integration.
    
    Provides pre-configured label styles with variants and sizes.
    
    Args:
        variant: Label style variant ('primary', 'secondary', 'tertiary', 'success', 'warning', 'error', 'info')
        size: Label size ('xs', 'sm', 'base', 'md', 'lg', 'xl')
        **kwargs: Additional arguments passed to CTkLabel
    """
    
    def __init__(
        self,
        master,
        variant: str = "primary",
        size: str = "base",
        **kwargs
    ):
        # Get text color based on variant
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            variant_colors = {
                "primary": AppColors.TEXT_PRIMARY,
                "secondary": AppColors.TEXT_SECONDARY,
                "tertiary": AppColors.TEXT_TERTIARY,
                "success": AppColors.SUCCESS_LIGHT,
                "warning": AppColors.WARNING_LIGHT,
                "error": AppColors.ERROR_LIGHT,
                "info": AppColors.INFO_LIGHT,
            }
        else:
            variant_colors = {
                "primary": AppColors.TEXT_PRIMARY_LIGHT,
                "secondary": AppColors.TEXT_SECONDARY_LIGHT,
                "tertiary": AppColors.TEXT_TERTIARY_LIGHT,
                "success": AppColors.SUCCESS_DARK,
                "warning": AppColors.WARNING_DARK,
                "error": AppColors.ERROR_DARK,
                "info": AppColors.INFO_DARK,
            }
        
        text_color = variant_colors.get(variant, variant_colors["primary"])
        
        # Get font size based on size
        size_fonts = {
            "xs": AppFont.SIZE_XS,
            "sm": AppFont.SIZE_SM,
            "base": AppFont.SIZE_BASE,
            "md": AppFont.SIZE_MD,
            "lg": AppFont.SIZE_LG,
            "xl": AppFont.SIZE_XL,
        }
        font_size = size_fonts.get(size, AppFont.SIZE_BASE)
        
        # Set default values
        defaults = {
            "text_color": text_color,
            "font": (AppFont.FAMILY_BASE[0], font_size),
        }
        
        # Merge defaults with user kwargs (user kwargs take precedence)
        final_kwargs = {**defaults, **kwargs}
        
        super().__init__(master, **final_kwargs)


class ModernCard(ctk.CTkFrame):
    """
    Modern card component with design system integration.
    
    Provides a card container with optional title and consistent styling.
    
    Args:
        title: Optional title text for the card
        **kwargs: Additional arguments passed to CTkFrame
    """
    
    def __init__(self, master, title: str = None, **kwargs):
        mode = ctk.get_appearance_mode()
        bg_color = AppColors.BG_SECONDARY if mode == "Dark" else AppColors.BG_SECONDARY_LIGHT
        
        # Set default values
        defaults = {
            "fg_color": bg_color,
            "corner_radius": VisualConstants.BORDER_RADIUS_LG,
            "border_width": VisualConstants.BORDER_WIDTH_THIN,
            "border_color": AppColors.BORDER_LIGHT if mode == "Dark" else AppColors.BORDER_LIGHT_LIGHT,
        }
        
        # Merge defaults with user kwargs (user kwargs take precedence)
        final_kwargs = {**defaults, **kwargs}
        
        super().__init__(master, **final_kwargs)
        
        # Add title if provided
        if title:
            title_frame = ctk.CTkFrame(self, fg_color="transparent")
            title_frame.pack(fill="x", padx=AppSpacing.LG, pady=(AppSpacing.LG, AppSpacing.SM))
            
            title_label = ModernLabel(
                title_frame,
                text=title,
                size="lg",
                variant="primary"
            )
            title_label.pack(side="left")
            
            # Add separator
            separator = ctk.CTkFrame(
                self,
                fg_color=AppColors.BORDER_LIGHT if mode == "Dark" else AppColors.BORDER_LIGHT_LIGHT,
                height=1
            )
            separator.pack(fill="x", padx=AppSpacing.LG, pady=(0, AppSpacing.MD))


class ModernTable(ctk.CTkFrame):
    """
    Modern table component with design system integration.
    
    Provides a table with headers and scrollable body with alternating row colors.
    
    Args:
        columns: List of column header names
        data: List of lists containing row data
        **kwargs: Additional arguments passed to CTkFrame
    """
    
    def __init__(self, master, columns: list, data: list = None, **kwargs):
        mode = ctk.get_appearance_mode()
        bg_color = AppColors.BG_PRIMARY if mode == "Dark" else AppColors.BG_PRIMARY_LIGHT
        
        # Set default values
        defaults = {
            "fg_color": bg_color,
            "corner_radius": VisualConstants.BORDER_RADIUS_MD,
            "border_width": VisualConstants.BORDER_WIDTH_THIN,
            "border_color": AppColors.BORDER_LIGHT if mode == "Dark" else AppColors.BORDER_LIGHT_LIGHT,
        }
        
        # Merge defaults with user kwargs (user kwargs take precedence)
        final_kwargs = {**defaults, **kwargs}
        
        super().__init__(master, **final_kwargs)
        
        # Header frame
        header_frame = ctk.CTkFrame(self, fg_color=AppColors.BG_TERTIARY if mode == "Dark" else AppColors.BG_TERTIARY_LIGHT)
        header_frame.pack(fill="x", padx=1, pady=1)
        
        # Configure header columns
        for col in range(len(columns)):
            header_frame.grid_columnconfigure(col, weight=1)
        
        # Header labels
        for col, text in enumerate(columns):
            header_label = ModernLabel(
                header_frame,
                text=text,
                size="sm",
                variant="primary"
            )
            header_label.grid(
                row=0,
                column=col,
                padx=AppSpacing.TABLE_CELL_PADDING_H,
                pady=AppSpacing.TABLE_CELL_PADDING_V,
                sticky="ew"
            )
        
        # Scrollable body
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=bg_color
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Configure scrollable frame columns
        for col in range(len(columns)):
            self.scrollable_frame.grid_columnconfigure(col, weight=1)
        
        # Populate data if provided
        if data:
            self.populate_data(data)
    
    def populate_data(self, data: list):
        """
        Populates the table with data.
        
        Args:
            data: List of lists containing row data
        """
        mode = ctk.get_appearance_mode()
        
        for i, row_data in enumerate(data):
            # Create row frame
            is_even = i % 2 == 0
            row_bg = AppColors.ROW_EVEN if (mode == "Dark" and is_even) else (
                AppColors.ROW_ODD if mode == "Dark" else (
                    AppColors.ROW_EVEN_LIGHT if is_even else AppColors.ROW_ODD_LIGHT
                )
            )
            
            row_frame = ctk.CTkFrame(
                self.scrollable_frame,
                fg_color=row_bg,
                border_width=VisualConstants.BORDER_WIDTH_THIN,
                border_color=AppColors.BORDER_LIGHT if mode == "Dark" else AppColors.BORDER_LIGHT_LIGHT
            )
            row_frame.grid(row=i, column=0, columnspan=len(row_data), sticky="ew", padx=1, pady=1)
            
            # Configure row columns
            for col in range(len(row_data)):
                row_frame.grid_columnconfigure(col, weight=1)
            
            # Add cell data
            for col, cell_data in enumerate(row_data):
                cell_label = ModernLabel(
                    row_frame,
                    text=str(cell_data) if cell_data is not None else "",
                    size="sm",
                    variant="secondary"
                )
                cell_label.grid(
                    row=0,
                    column=col,
                    padx=AppSpacing.TABLE_CELL_PADDING_H,
                    pady=AppSpacing.TABLE_CELL_PADDING_V,
                    sticky="w"
                )

