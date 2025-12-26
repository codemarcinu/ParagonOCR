"""
AI Chat Tab Component for ParagonOCR 2.0

Provides a chat interface for interacting with the AI assistant using RAG.

Author: ParagonOCR Team
Version: 2.0
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable, List, Dict
from datetime import datetime
import threading
import logging

from .unified_design_system import AppColors, AppSpacing, AppFont, Icons

logger = logging.getLogger(__name__)


class AIChatTab(ctk.CTkFrame):
    """
    AI Chat tab component with message history, input area, and chat header.
    
    Provides a complete chat interface for user-AI interactions with
    RAG-powered context retrieval.
    
    Attributes:
        parent: Parent window/widget
        on_send_message: Callback function when user sends a message
        on_clear_history: Callback function to clear chat history
        on_export_conversation: Callback function to export conversation
        on_conversation_change: Callback function when conversation changes
    """
    
    def __init__(
        self,
        parent: ctk.CTk,
        on_send_message: Optional[Callable[[str], None]] = None,
        on_clear_history: Optional[Callable[[], None]] = None,
        on_export_conversation: Optional[Callable[[], None]] = None,
        on_conversation_change: Optional[Callable[[int], None]] = None
    ) -> None:
        """
        Initialize the AI Chat tab.
        
        Args:
            parent: Parent window/widget
            on_send_message: Callback when user sends a message (message: str)
            on_clear_history: Callback to clear chat history
            on_export_conversation: Callback to export conversation
            on_conversation_change: Callback when conversation changes (conversation_id: int)
        """
        super().__init__(parent)
        
        self.on_send_message = on_send_message
        self.on_clear_history = on_clear_history
        self.on_export_conversation = on_export_conversation
        self.on_conversation_change = on_conversation_change
        
        self.messages: List[Dict] = []
        self.current_conversation_id: Optional[int] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Chat Header
        self._create_chat_header()
        
        # Message History Widget
        self._create_message_history()
        
        # Input Area
        self._create_input_area()
    
    def _create_chat_header(self) -> None:
        """Create the chat header with title, buttons, and conversation dropdown."""
        header_frame = ctk.CTkFrame(
            self,
            border_width=1,
            border_color=AppColors.BORDER_DARK
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Conversation title
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=f"{Icons.CHAT} Nowa rozmowa",
            font=(AppFont.FAMILY, AppFont.SIZE_LG, "bold")
        )
        self.title_label.grid(row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w")
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(header_frame)
        buttons_frame.grid(row=0, column=1, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="e")
        
        # Conversation dropdown
        self.conversation_combo = ctk.CTkComboBox(
            buttons_frame,
            values=["Nowa rozmowa"],
            command=self._on_conversation_selected,
            width=200
        )
        self.conversation_combo.pack(side="left", padx=AppSpacing.XS)
        self.conversation_combo.set("Nowa rozmowa")
        
        # Clear history button
        btn_clear = ctk.CTkButton(
            buttons_frame,
            text=f"{Icons.CLEAR} Wyczyść",
            command=self._on_clear_clicked,
            width=100,
            fg_color=AppColors.WARNING,
            hover_color=self._adjust_color(AppColors.WARNING, -15)
        )
        btn_clear.pack(side="left", padx=AppSpacing.XS)
        
        # Export button
        btn_export = ctk.CTkButton(
            buttons_frame,
            text=f"{Icons.EXPORT} Eksportuj",
            command=self._on_export_clicked,
            width=100,
            fg_color=AppColors.INFO,
            hover_color=self._adjust_color(AppColors.INFO, -15)
        )
        btn_export.pack(side="left", padx=AppSpacing.XS)
    
    def _create_message_history(self) -> None:
        """Create the message history widget with auto-scroll."""
        # Scrollable frame for messages
        self.message_frame = ctk.CTkScrollableFrame(
            self,
            border_width=1,
            border_color=AppColors.BORDER_DARK
        )
        self.message_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=AppSpacing.SM,
            pady=AppSpacing.SM
        )
        self.message_frame.grid_columnconfigure(0, weight=1)
    
    def _create_input_area(self) -> None:
        """Create the input area with multi-line text, send button, and character counter."""
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=2, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Input text area (multi-line)
        self.input_textbox = ctk.CTkTextbox(
            input_frame,
            height=100,
            wrap="word",
            font=(AppFont.FAMILY, AppFont.SIZE_MD)
        )
        self.input_textbox.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=AppSpacing.SM,
            pady=AppSpacing.SM
        )
        self.input_textbox.bind("<Control-Return>", lambda e: self._on_send_clicked())
        
        # Character counter
        self.char_counter = ctk.CTkLabel(
            input_frame,
            text="0 znaków",
            font=(AppFont.FAMILY, AppFont.SIZE_XS),
            text_color=AppColors.UNKNOWN
        )
        self.char_counter.grid(
            row=1,
            column=0,
            padx=AppSpacing.SM,
            pady=AppSpacing.XS,
            sticky="w"
        )
        
        # Update character counter on text change
        self.input_textbox.bind("<KeyRelease>", self._update_char_counter)
        self.input_textbox.bind("<Button-1>", self._update_char_counter)
        
        # Send button
        btn_send = ctk.CTkButton(
            input_frame,
            text=f"{Icons.SEND} Wyślij",
            command=self._on_send_clicked,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=self._adjust_color(AppColors.PRIMARY, -15)
        )
        btn_send.grid(row=1, column=1, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="e")
    
    def _update_char_counter(self, event=None) -> None:
        """Update the character counter."""
        text = self.input_textbox.get("1.0", "end-1c")
        char_count = len(text)
        self.char_counter.configure(text=f"{char_count} znaków")
    
    def _on_send_clicked(self) -> None:
        """Handle send button click."""
        message = self.input_textbox.get("1.0", "end-1c").strip()
        if not message:
            return
        
        # Clear input
        self.input_textbox.delete("1.0", "end")
        self._update_char_counter()
        
        # Add user message to history
        self.add_message("user", message)
        
        # Call callback
        if self.on_send_message:
            try:
                self.on_send_message(message)
            except Exception as e:
                logger.error(f"Error in on_send_message callback: {e}")
    
    def _on_clear_clicked(self) -> None:
        """Handle clear history button click."""
        if self.on_clear_history:
            try:
                self.on_clear_history()
            except Exception as e:
                logger.error(f"Error in on_clear_history callback: {e}")
        self.clear_messages()
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        if self.on_export_conversation:
            try:
                self.on_export_conversation()
            except Exception as e:
                logger.error(f"Error in on_export_conversation callback: {e}")
    
    def _on_conversation_selected(self, choice: str) -> None:
        """Handle conversation dropdown selection."""
        if choice == "Nowa rozmowa":
            self.current_conversation_id = None
            if self.on_conversation_change:
                try:
                    self.on_conversation_change(-1)
                except Exception as e:
                    logger.error(f"Error in on_conversation_change callback: {e}")
        else:
            # Extract conversation ID from choice if needed
            # For now, just log
            logger.info(f"Selected conversation: {choice}")
    
    def add_message(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        response_time_ms: Optional[int] = None
    ) -> None:
        """
        Add a message to the chat history.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            timestamp: Message timestamp (defaults to now)
            response_time_ms: Response time in milliseconds (for AI messages)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        message_data = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "response_time_ms": response_time_ms
        }
        self.messages.append(message_data)
        
        # Create message widget
        self._create_message_widget(message_data)
        
        # Auto-scroll to newest
        self._scroll_to_bottom()
    
    def _create_message_widget(self, message_data: Dict) -> None:
        """Create a message widget in the chat history."""
        role = message_data["role"]
        content = message_data["content"]
        timestamp = message_data["timestamp"]
        response_time = message_data.get("response_time_ms")
        
        # Message container frame
        msg_frame = ctk.CTkFrame(
            self.message_frame,
            fg_color=AppColors.SURFACE_DARK if role == "user" else AppColors.BG_DARK
        )
        msg_frame.grid(
            row=len(self.messages) - 1,
            column=0,
            sticky="ew",
            padx=AppSpacing.SM,
            pady=AppSpacing.XS
        )
        msg_frame.grid_columnconfigure(0, weight=1)
        
        # Header with role, timestamp, and copy button
        header_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.XS, pady=AppSpacing.XS)
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Role label with color
        role_color = AppColors.INFO if role == "user" else AppColors.SUCCESS
        role_text = "Ty" if role == "user" else "AI"
        role_label = ctk.CTkLabel(
            header_frame,
            text=role_text,
            font=(AppFont.FAMILY, AppFont.SIZE_SM, "bold"),
            text_color=role_color
        )
        role_label.grid(row=0, column=0, padx=AppSpacing.XS, sticky="w")
        
        # Timestamp
        time_str = timestamp.strftime("%H:%M:%S")
        time_label = ctk.CTkLabel(
            header_frame,
            text=time_str,
            font=(AppFont.FAMILY, AppFont.SIZE_XS),
            text_color=AppColors.UNKNOWN
        )
        time_label.grid(row=0, column=1, padx=AppSpacing.XS, sticky="e")
        
        # Response time (for AI messages)
        if response_time is not None and role == "assistant":
            response_time_str = f"{response_time}ms"
            response_label = ctk.CTkLabel(
                header_frame,
                text=response_time_str,
                font=(AppFont.FAMILY, AppFont.SIZE_XS),
                text_color=AppColors.UNKNOWN
            )
            response_label.grid(row=0, column=2, padx=AppSpacing.XS, sticky="e")
        
        # Copy button (shown on hover - simplified for now)
        copy_btn = ctk.CTkButton(
            header_frame,
            text=Icons.COPY,
            width=30,
            height=20,
            font=(AppFont.FAMILY, AppFont.SIZE_XS),
            command=lambda c=content: self._copy_to_clipboard(c),
            fg_color="transparent",
            hover_color=AppColors.BORDER_DARK
        )
        copy_btn.grid(row=0, column=3, padx=AppSpacing.XS, sticky="e")
        
        # Message content
        content_label = ctk.CTkLabel(
            msg_frame,
            text=content,
            font=(AppFont.FAMILY, AppFont.SIZE_MD),
            wraplength=600,
            justify="left",
            anchor="w"
        )
        content_label.grid(
            row=1,
            column=0,
            padx=AppSpacing.SM,
            pady=AppSpacing.XS,
            sticky="w"
        )
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            # Could show a toast notification here
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
    
    def _scroll_to_bottom(self) -> None:
        """Auto-scroll to the newest message."""
        try:
            self.message_frame.update()
            # Scroll to bottom by setting scrollbar position
            # CustomTkinter doesn't have direct scroll_to method, so we use after
            self.after(100, lambda: self.message_frame._parent_canvas.yview_moveto(1.0))
        except Exception as e:
            logger.error(f"Error scrolling to bottom: {e}")
    
    def clear_messages(self) -> None:
        """Clear all messages from the chat history."""
        self.messages = []
        for widget in self.message_frame.winfo_children():
            widget.destroy()
    
    def set_conversation_title(self, title: str) -> None:
        """
        Set the conversation title.
        
        Args:
            title: Conversation title
        """
        self.title_label.configure(text=f"{Icons.CHAT} {title}")
    
    def set_conversations_list(self, conversations: List[Dict]) -> None:
        """
        Update the conversations dropdown list.
        
        Args:
            conversations: List of conversation dicts with 'id' and 'title' keys
        """
        values = ["Nowa rozmowa"]
        for conv in conversations:
            title = conv.get("title", f"Rozmowa {conv.get('id', '?')}")
            values.append(title)
        
        self.conversation_combo.configure(values=values)
    
    def set_current_conversation(self, conversation_id: Optional[int]) -> None:
        """
        Set the current conversation ID.
        
        Args:
            conversation_id: Conversation ID or None for new conversation
            
        Raises:
            ValueError: If conversation_id is negative
        """
        if conversation_id is not None and conversation_id < 0:
            raise ValueError(f"Invalid conversation_id: {conversation_id}. Must be non-negative or None.")
        self.current_conversation_id = conversation_id
    
    @staticmethod
    def _adjust_color(color: str, amount: int) -> str:
        """
        Adjust color brightness.
        
        Args:
            color: Hex color string
            amount: Amount to adjust (-255 to 255)
            
        Returns:
            Adjusted hex color string
        """
        try:
            color = color.lstrip("#")
            rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
            new_rgb = tuple(max(0, min(255, c + amount)) for c in rgb)
            return "#%02x%02x%02x" % new_rgb
        except Exception:
            return color

