import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading

from core.processor import get_images_from_folder, process_pair
from ui.widgets import (
    ThumbnailCard, CropRegionPicker, PairPreview,
    COLOR_BG, COLOR_CARD, COLOR_CARD_HOVER, COLOR_ACCENT, COLOR_ACCENT2,
    COLOR_TEXT, COLOR_MUTED, COLOR_BORDER_NORM,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("32:9 Wallpaper Compiler")
        self.geometry("1440x940")
        self.minsize(1200, 900)
        self.configure(fg_color=COLOR_BG)

        self.input_folder: Path | None = None
        self.output_folder: Path | None = None
        self.images: list[Path] = []
        self.cards: list[ThumbnailCard] = []

        self._left_path: Path | None = None
        self._right_path: Path | None = None
        self._left_card: ThumbnailCard | None = None
        self._right_card: ThumbnailCard | None = None
        self._next_side = "left"  # перший клік = left, другий = right

        self._build_ui()

    # ─── UI BUILD ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Хедер
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="◈  32:9 WALLPAPER COMPILER",
            font=("Courier New", 18, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(side="left", padx=24, pady=16)

        ctk.CTkLabel(
            header,
            text="10240×2880 output",
            font=("Courier New", 12),
            text_color=COLOR_MUTED,
        ).pack(side="left", padx=0, pady=16)

        # Кнопки папок у хедері
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=16)

        self._lbl_input = ctk.CTkLabel(
            btn_frame, text="No input folder",
            font=("Courier New", 11), text_color=COLOR_MUTED,
        )
        self._lbl_input.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="📁 Input", width=100,
            font=("Courier New", 12, "bold"),
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            border_width=1, border_color=COLOR_BORDER_NORM,
            command=self._choose_input,
        ).pack(side="left", padx=4)

        self._lbl_output = ctk.CTkLabel(
            btn_frame, text="No output folder",
            font=("Courier New", 11), text_color=COLOR_MUTED,
        )
        self._lbl_output.pack(side="left", padx=(16, 8))

        ctk.CTkButton(
            btn_frame, text="📂 Output", width=100,
            font=("Courier New", 12, "bold"),
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER,
            border_width=1, border_color=COLOR_BORDER_NORM,
            command=self._choose_output,
        ).pack(side="left", padx=4)

        # Основна область
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=12)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)

        # Ліва панель — грід мініатюр
        self._build_grid_panel(main)

        # Права панель — налаштування та превью
        self._build_control_panel(main)

    def _build_grid_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            frame,
            text="WALLPAPERS",
            font=("Courier New", 13, "bold"),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            frame,
            text="Click card = auto-assign  ·  Click  L / R  badge = force assign",
            font=("Courier New", 10),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # Scrollable грід
        self._scroll = ctk.CTkScrollableFrame(
            frame, fg_color="transparent",
            scrollbar_button_color=COLOR_ACCENT,
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_control_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="transparent", width=680)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.pack_propagate(False)
        panel.configure(width=680)

        # Превью
        ctk.CTkLabel(
            panel,
            text="PREVIEW  32:9",
            font=("Courier New", 13, "bold"),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(0, 4))

        self._preview = PairPreview(panel)
        self._preview.pack(fill="x")

        # Crop region pickers
        crop_frame = ctk.CTkFrame(panel, fg_color=COLOR_CARD, corner_radius=10)
        crop_frame.pack(fill="x", pady=12)

        self._crop_left = CropRegionPicker(crop_frame, label="LEFT", on_change=self._refresh_preview)
        self._crop_left.pack(padx=10, pady=(10, 4))

        sep = ctk.CTkFrame(crop_frame, height=1, fg_color=COLOR_BORDER_NORM)
        sep.pack(fill="x", padx=10, pady=2)

        self._crop_right = CropRegionPicker(crop_frame, label="RIGHT", on_change=self._refresh_preview)
        self._crop_right.pack(padx=10, pady=(4, 10))

        # Якість / ім'я файлу
        opts_frame = ctk.CTkFrame(panel, fg_color=COLOR_CARD, corner_radius=10)
        opts_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            opts_frame, text="OUTPUT FILENAME",
            font=("Courier New", 11), text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self._filename_entry = ctk.CTkEntry(
            opts_frame,
            placeholder_text="auto-generated if empty",
            font=("Courier New", 12),
            fg_color="#111111",
            border_color=COLOR_BORDER_NORM,
        )
        self._filename_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            opts_frame, text="JPEG QUALITY",
            font=("Courier New", 11), text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=12)

        quality_row = ctk.CTkFrame(opts_frame, fg_color="transparent")
        quality_row.pack(fill="x", padx=12, pady=(4, 10))

        self._quality_label = ctk.CTkLabel(
            quality_row, text="95",
            font=("Courier New", 13, "bold"),
            text_color=COLOR_ACCENT2, width=32,
        )
        self._quality_label.pack(side="left")

        self._quality_slider = ctk.CTkSlider(
            quality_row, from_=60, to=100,
            number_of_steps=40,
            button_color=COLOR_ACCENT2,
            progress_color=COLOR_ACCENT2,
            command=lambda v: self._quality_label.configure(text=str(int(v))),
        )
        self._quality_slider.set(95)
        self._quality_slider.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Кнопка генерації
        self._btn_generate = ctk.CTkButton(
            panel,
            text="⚡  GENERATE  10240×2880",
            font=("Courier New", 15, "bold"),
            text_color="white",
            height=52,
            fg_color="#2d8a4e",
            hover_color="#236b3d",
            corner_radius=10,
            command=self._generate,
        )
        self._btn_generate.pack(fill="x", pady=(0, 8))

        # Статус
        self._status = ctk.CTkLabel(
            panel, text="Select input folder to start",
            font=("Courier New", 11),
            text_color=COLOR_MUTED,
            wraplength=320,
        )
        self._status.pack(anchor="w")

    # ─── LOGIC ───────────────────────────────────────────────────────────────

    def _choose_input(self):
        folder = filedialog.askdirectory(title="Select folder with wallpapers")
        if not folder:
            return
        self.input_folder = Path(folder)
        self._lbl_input.configure(text=self.input_folder.name, text_color=COLOR_ACCENT2)

        # Якщо output не встановлено — пропонуємо підпапку
        if self.output_folder is None:
            self.output_folder = self.input_folder / "compiled"
            self._lbl_output.configure(text="compiled/", text_color=COLOR_ACCENT2)

        self._load_images()

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if not folder:
            return
        self.output_folder = Path(folder)
        self._lbl_output.configure(text=self.output_folder.name, text_color=COLOR_ACCENT2)

    def _load_images(self):
        self.images = get_images_from_folder(self.input_folder)
        self._clear_selection()
        self._render_grid()
        self._status.configure(text=f"{len(self.images)} images found")

    def _render_grid(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self.cards.clear()

        COLS = 3
        for i, path in enumerate(self.images):
            card = ThumbnailCard(self._scroll, path, on_select=self._on_card_click)
            card.grid(row=i // COLS, column=i % COLS, padx=6, pady=6, sticky="nw")
            self.cards.append(card)

    def _on_card_click(self, card: ThumbnailCard, side: str | None = None):
        if side is not None:
            # Badge click — force-assign to specific side
            if card.selection == side:
                # Already on this side → deselect
                self._deselect(card, side)
            else:
                # Remove from opposite side if previously assigned there
                if card.selection is not None:
                    self._deselect(card, card.selection)
                self._assign(card, side)
        else:
            # Body click — auto-rotate: unselected→next_side, selected→deselect
            if card.selection is None:
                self._assign(card, self._next_side)
            else:
                self._deselect(card, card.selection)

        self._refresh_preview()

    def _assign(self, card: ThumbnailCard, side: str):
        if side == "left":
            if self._left_card and self._left_card is not card:
                self._left_card.set_selection(None)
            self._left_card = card
            self._left_path = card.image_path
            self._next_side = "right"
            card.set_selection("left")
            self._crop_left.load_image(card.image_path)
        else:
            if self._right_card and self._right_card is not card:
                self._right_card.set_selection(None)
            self._right_card = card
            self._right_path = card.image_path
            self._next_side = "left"
            card.set_selection("right")
            self._crop_right.load_image(card.image_path)

    def _deselect(self, card: ThumbnailCard, side: str):
        if side == "left":
            self._left_card = None
            self._left_path = None
            self._next_side = "left"
            self._crop_left.reset()
        else:
            self._right_card = None
            self._right_path = None
            self._next_side = "right"
            self._crop_right.reset()
        card.set_selection(None)

    def _clear_selection(self):
        self._left_path = None
        self._right_path = None
        self._left_card = None
        self._right_card = None
        self._next_side = "left"
        self._crop_left.reset()
        self._crop_right.reset()

    def _refresh_preview(self):
        self._preview.update_preview(
            self._left_path,
            self._right_path,
            left_anchor=self._crop_left.get_anchor(),
            right_anchor=self._crop_right.get_anchor(),
            left_rotation=self._crop_left.get_rotation(),
            right_rotation=self._crop_right.get_rotation(),
        )

    def _generate(self):
        if not self._left_path or not self._right_path:
            self._status.configure(text="⚠ Select LEFT and RIGHT images first", text_color=COLOR_ACCENT)
            return
        if not self.output_folder:
            self._status.configure(text="⚠ Select output folder", text_color=COLOR_ACCENT)
            return

        filename = self._filename_entry.get().strip()
        if not filename:
            left_stem = self._left_path.stem[:12]
            right_stem = self._right_path.stem[:12]
            filename = f"{left_stem}_x_{right_stem}.jpg"
        elif not filename.lower().endswith((".jpg", ".jpeg")):
            filename += ".jpg"

        output_path = self.output_folder / filename
        quality = int(self._quality_slider.get())

        self._btn_generate.configure(state="disabled", text="⏳ Processing...")
        self._status.configure(text="Generating...", text_color=COLOR_MUTED)

        def run():
            try:
                result = process_pair(
                    self._left_path,
                    self._right_path,
                    output_path,
                    left_anchor=self._crop_left.get_anchor(),
                    right_anchor=self._crop_right.get_anchor(),
                    quality=quality,
                    left_rotation=self._crop_left.get_rotation(),
                    right_rotation=self._crop_right.get_rotation(),
                )
                self.after(0, lambda: self._on_done(result))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, path: Path):
        self._btn_generate.configure(state="normal", text="⚡  GENERATE  10240×2880")
        self._status.configure(
            text=f"✓ Saved: {path.name}",
            text_color=COLOR_ACCENT2,
        )
        self._filename_entry.delete(0, "end")

    def _on_error(self, err: str):
        self._btn_generate.configure(state="normal", text="⚡  GENERATE  10240×2880")
        self._status.configure(text=f"✗ Error: {err}", text_color=COLOR_ACCENT)
