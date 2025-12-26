"""
Notification System for ParagonOCR 2.0

Provides toast notifications and dialog boxes for user feedback.

Author: ParagonOCR Team
Version: 2.0
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable
import threading
import logging

from .unified_design_system import AppColors, AppSpacing, AppFont, Icons

logger = logging.getLogger(__name__)


class NotificationToast:
    """
    Toast notification system for displaying temporary messages.
    
    Provides non-blocking toast notifications that automatically disappear
    after a specified duration. Supports success, error, warning, and info types.
    
    Attributes:
        parent: Parent window/widget for the toast
        toasts: List of active toast widgets
    """
    
    def __init__(self, parent: ctk.CTk) -> None:
        """
        Initialize the notification toast system.
        
        Args:
            parent: Parent window/widget where toasts will be displayed
        """
        self.parent = parent
        self.toasts: list[ctk.CTkToplevel] = []
    
    def show_success(
        self,
        message: str,
        duration_ms: int = 3000
    ) -> None:
        """
        Display a success toast notification.
        
        Args:
            message: Message text to display
            duration_ms: Duration in milliseconds before auto-dismiss (default: 3000)
        """
        self._show_toast(message, AppColors.SUCCESS, Icons.SUCCESS, duration_ms)
    
    def show_error(
        self,
        message: str,
        duration_ms: int = 5000
    ) -> None:
        """
        Display an error toast notification.
        
        Args:
            message: Message text to display
            duration_ms: Duration in milliseconds before auto-dismiss (default: 5000)
        """
        self._show_toast(message, AppColors.ERROR, Icons.ERROR, duration_ms)
    
    def show_warning(
        self,
        message: str,
        duration_ms: int = 4000
    ) -> None:
        """
        Display a warning toast notification.
        
        Args:
            message: Message text to display
            duration_ms: Duration in milliseconds before auto-dismiss (default: 4000)
        """
        self._show_toast(message, AppColors.WARNING, Icons.WARNING, duration_ms)
    
    def show_info(
        self,
        message: str,
        duration_ms: int = 3000
    ) -> None:
        """
        Display an info toast notification.
        
        Args:
            message: Message text to display
            duration_ms: Duration in milliseconds before auto-dismiss (default: 3000)
        """
        self._show_toast(message, AppColors.INFO, "ℹ️", duration_ms)
    
    def _show_toast(
        self,
        message: str,
        color: str,
        icon: str,
        duration_ms: int
    ) -> None:
        """
        Internal method to create and display a toast notification.
        
        Args:
            message: Message text to display
            color: Background color for the toast
            icon: Icon emoji to display
            duration_ms: Duration in milliseconds before auto-dismiss
        """
        try:
            # Create toast window
            toast = ctk.CTkToplevel(self.parent)
            toast.overrideredirect(True)  # Remove window decorations
            toast.attributes("-topmost", True)  # Keep on top
            
            # Calculate position (top-right corner)
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            
            toast_width = 350
            toast_height = 80
            x = parent_x + parent_width - toast_width - AppSpacing.LG
            y = parent_y + AppSpacing.LG
            
            toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
            
            # Create frame with colored background
            frame = ctk.CTkFrame(
                toast,
                fg_color=color,
                corner_radius=AppSpacing.SM
            )
            frame.pack(fill="both", expand=True, padx=AppSpacing.XS, pady=AppSpacing.XS)
            
            # Create label with message
            label = ctk.CTkLabel(
                frame,
                text=f"{icon} {message}",
                font=(AppFont.FAMILY, AppFont.SIZE_MD),
                text_color="white",
                wraplength=toast_width - AppSpacing.LG
            )
            label.pack(
                fill="both",
                expand=True,
                padx=AppSpacing.SM,
                pady=AppSpacing.SM
            )
            
            # Store toast reference
            self.toasts.append(toast)
            
            # Auto-dismiss after duration
            def dismiss() -> None:
                try:
                    if toast.winfo_exists():
                        toast.destroy()
                    if toast in self.toasts:
                        self.toasts.remove(toast)
                except Exception as e:
                    logger.error(f"Error dismissing toast: {e}")
            
            toast.after(duration_ms, dismiss)
            
            # Show toast
            toast.update()
            
        except Exception as e:
            logger.error(f"Error showing toast notification: {e}")
            # Fallback to messagebox for critical errors
            messagebox.showinfo("Notification", message)


class NotificationDialog:
    """
    Dialog system for user confirmation and alerts.
    
    Provides blocking dialog boxes for user interaction, including
    confirmation dialogs and alert messages.
    """
    
    def __init__(self, parent: ctk.CTk) -> None:
        """
        Initialize the notification dialog system.
        
        Args:
            parent: Parent window/widget for dialogs
        """
        self.parent = parent
    
    def confirm(
        self,
        title: str,
        message: str
    ) -> bool:
        """
        Display a confirmation dialog and return user's choice.
        
        Args:
            title: Dialog title
            message: Message text to display
            
        Returns:
            True if user confirmed, False otherwise
        """
        try:
            result = messagebox.askyesno(
                title,
                message,
                parent=self.parent
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Error showing confirmation dialog: {e}")
            # Fallback: assume user declined
            return False
    
    def alert(
        self,
        title: str,
        message: str
    ) -> None:
        """
        Display an alert dialog.
        
        Args:
            title: Dialog title
            message: Message text to display
        """
        try:
            messagebox.showinfo(
                title,
                message,
                parent=self.parent
            )
        except Exception as e:
            logger.error(f"Error showing alert dialog: {e}")

