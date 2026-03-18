import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
from pathlib import Path
import threading


CARD_W = 220
CARD_H = 178
THUMB_W = 200
THUMB_H = 113

COLOR_BG = "#161616"
COLOR_CARD = "#1e1e1e"
COLOR_CARD_HOVER = "#2a2a2a"
COLOR_SELECTED = "#252525"
COLOR_ACCENT = "#e8e8e8"
COLOR_ACCENT2 = "#909090"
COLOR_TEXT = "#f0f0f0"
COLOR_MUTED = "#6e6e6e"
COLOR_BORDER_SEL = "#cccccc"
COLOR_BORDER_NORM = "#353535"


class ThumbnailCard(ctk.CTkFrame):
    """Картка з мініатюрою зображення, підтримує вибір (ліво/право)."""

    def __init__(self, master, image_path: Path, on_select, **kwargs):
        super().__init__(
            master,
            width=CARD_W,
            height=CARD_H,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=2,
            border_color=COLOR_BORDER_NORM,
            **kwargs,
        )
        self.image_path = image_path
        self.on_select = on_select
        self.selection: str | None = None  # "left" | "right" | None
        self._photo = None
        self._build()
        self._load_thumbnail()
        self.bind("<Button-1>", self._on_click)

    def _build(self):
        self.grid_propagate(False)
        self.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(self, text="", width=THUMB_W, height=THUMB_H)
        self.thumb_label.place(x=10, y=8)
        self.thumb_label.bind("<Button-1>", self._on_click)

        name = self.image_path.name
        if len(name) > 26:
            name = name[:23] + "..."
        self.name_label = ctk.CTkLabel(
            self, text=name,
            font=("Courier New", 11),
            text_color=COLOR_MUTED,
            width=CARD_W - 20,
            anchor="w",
        )
        self.name_label.place(x=10, y=THUMB_H + 12)
        self.name_label.bind("<Button-1>", self._on_click)

        # Бейджи L / R (клікабельні)
        self.badge_l = ctk.CTkLabel(
            self, text=" L ", width=28, height=20,
            font=("Courier New", 11, "bold"),
            fg_color=COLOR_BG, text_color=COLOR_MUTED,
            corner_radius=4, cursor="hand2",
        )
        self.badge_l.place(x=10, y=THUMB_H + 34)
        self.badge_l.bind("<Button-1>", self._on_badge_l_click)

        self.badge_r = ctk.CTkLabel(
            self, text=" R ", width=28, height=20,
            font=("Courier New", 11, "bold"),
            fg_color=COLOR_BG, text_color=COLOR_MUTED,
            corner_radius=4, cursor="hand2",
        )
        self.badge_r.place(x=44, y=THUMB_H + 34)
        self.badge_r.bind("<Button-1>", self._on_badge_r_click)

    def _load_thumbnail(self):
        def load():
            try:
                from core.processor import make_thumbnail
                thumb = make_thumbnail(self.image_path, (THUMB_W, THUMB_H))
                ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(THUMB_W, THUMB_H))
                self.after(0, lambda: self._set_image(ctk_img))
            except Exception:
                self.after(0, self._set_placeholder)

        threading.Thread(target=load, daemon=True).start()

    def _set_image(self, img):
        self._photo = img
        self.thumb_label.configure(image=img)

    def _set_placeholder(self):
        placeholder = Image.new("RGB", (THUMB_W, THUMB_H), (25, 25, 25))
        d = ImageDraw.Draw(placeholder)
        d.text((THUMB_W // 2 - 20, THUMB_H // 2 - 8), "?  err", fill=(80, 80, 80))
        ctk_img = ctk.CTkImage(light_image=placeholder, dark_image=placeholder, size=(THUMB_W, THUMB_H))
        self._photo = ctk_img
        self.thumb_label.configure(image=ctk_img)

    def _on_click(self, event=None):
        self.on_select(self)

    def _on_badge_l_click(self, event=None):
        self.on_select(self, "left")
        return "break"

    def _on_badge_r_click(self, event=None):
        self.on_select(self, "right")
        return "break"

    def set_selection(self, side: str | None):
        """side: 'left', 'right', None"""
        self.selection = side
        if side == "left":
            self.configure(border_color="#2d8a4e", fg_color=COLOR_SELECTED)
            self.badge_l.configure(fg_color="#2d8a4e", text_color="white")
            self.badge_r.configure(fg_color=COLOR_BG, text_color=COLOR_MUTED)
        elif side == "right":
            self.configure(border_color="#2a5fad", fg_color=COLOR_SELECTED)
            self.badge_l.configure(fg_color=COLOR_BG, text_color=COLOR_MUTED)
            self.badge_r.configure(fg_color="#2a5fad", text_color="white")
        else:
            self.configure(border_color=COLOR_BORDER_NORM, fg_color=COLOR_CARD)
            self.badge_l.configure(fg_color=COLOR_BG, text_color=COLOR_MUTED)
            self.badge_r.configure(fg_color=COLOR_BG, text_color=COLOR_MUTED)


def _outside_rects(
    ox: float, oy: float, dw: float, dh: float,
    x0: float, y0: float, x1: float, y1: float,
) -> list[tuple[float, float, float, float]]:
    """Four rects covering the image area outside the crop box."""
    return [
        (ox, oy, x0, oy + dh),       # left strip
        (x1, oy, ox + dw, oy + dh),  # right strip
        (x0, oy, x1, y0),            # top strip
        (x0, y1, x1, oy + dh),       # bottom strip
    ]


class CropRegionPicker(ctk.CTkFrame):
    """Shows image with a draggable 16:9 crop box. Drag to reposition crop area."""

    DISP_W = 620
    DISP_H = 120
    RATIO = 16 / 9

    def __init__(self, master, label: str = "", on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._anchor_x = 0.5
        self._anchor_y = 0.5
        self._orig_size: tuple[int, int] | None = None
        self._tk_img = None
        self._img_disp_size = (0, 0)
        self._img_offset = (0, 0)
        self._image_path: Path | None = None
        self._rotation_cw: int = 0
        self._dragging = False
        self._drag_start_px = (0, 0)
        self._drag_start_anchor = (0.5, 0.5)
        self._build(label)

    def _build(self, label: str):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 4))
        if label:
            ctk.CTkLabel(
                top_row, text=label,
                font=("Courier New", 11, "bold"),
                text_color=COLOR_MUTED,
            ).pack(side="left")
        ctk.CTkButton(
            top_row, text="↻  90°", width=64, height=22,
            font=("Courier New", 10),
            fg_color=COLOR_BG, hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_MUTED,
            border_width=1, border_color=COLOR_BORDER_NORM,
            corner_radius=4,
            command=self._rotate_cw,
        ).pack(side="right")
        self.canvas = tk.Canvas(
            self,
            width=self.DISP_W, height=self.DISP_H,
            bg=COLOR_CARD,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER_NORM,
            cursor="fleur",
        )
        self.canvas.pack()
        self._draw_placeholder()
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _draw_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.DISP_W // 2, self.DISP_H // 2,
            text="no image", fill=COLOR_MUTED,
            font=("Courier New", 10),
        )

    def load_image(self, path: Path):
        self._image_path = path
        self._rotation_cw = 0
        self._anchor_x = 0.5
        self._anchor_y = 0.5
        self._orig_size = None
        self._tk_img = None
        self._draw_placeholder()
        self._load_async()

    def _load_async(self):
        path = self._image_path
        rot = self._rotation_cw

        def _load():
            try:
                img = Image.open(path).convert("RGB")
                raw_w, raw_h = img.size
                # Apply CW rotation
                if rot == 90:
                    img = img.rotate(-90, expand=True)
                elif rot == 180:
                    img = img.rotate(180, expand=True)
                elif rot == 270:
                    img = img.rotate(90, expand=True)
                # Rotated dimensions for crop math
                orig_size = (raw_h, raw_w) if rot in (90, 270) else (raw_w, raw_h)
                iw, ih = img.size
                scale = min(self.DISP_W / iw, self.DISP_H / ih)
                dw = max(1, int(iw * scale))
                dh = max(1, int(ih * scale))
                disp = img.resize((dw, dh), Image.LANCZOS)
                self.after(0, lambda: self._set_image(orig_size, disp))
            except Exception:
                pass

        threading.Thread(target=_load, daemon=True).start()

    def _rotate_cw(self):
        if self._image_path is None:
            return
        self._rotation_cw = (self._rotation_cw + 90) % 360
        self._anchor_x = 0.5
        self._anchor_y = 0.5
        self._orig_size = None
        self._tk_img = None
        self._draw_placeholder()
        self._load_async()

    def get_rotation(self) -> int:
        return self._rotation_cw

    def _set_image(self, orig_size: tuple[int, int], disp: Image.Image):
        self._orig_size = orig_size
        dw, dh = disp.size
        self._img_disp_size = (dw, dh)
        self._img_offset = (
            (self.DISP_W - dw) // 2,
            (self.DISP_H - dh) // 2,
        )
        self._tk_img = ImageTk.PhotoImage(disp)
        self._redraw()

    def _get_crop_rect(self) -> tuple[float, float, float, float] | None:
        if self._orig_size is None:
            return None
        iw, ih = self._orig_size
        ox, oy = self._img_offset
        dw, dh = self._img_disp_size
        if dw == 0 or dh == 0:
            return None
        curr = iw / ih
        if curr > self.RATIO + 0.01:
            # Wider than 16:9 — box moves horizontally
            crop_w = dh * self.RATIO
            max_dx = dw - crop_w
            if max_dx <= 0:
                return (float(ox), float(oy), float(ox + dw), float(oy + dh))
            x0 = ox + max_dx * self._anchor_x
            return (x0, float(oy), x0 + crop_w, float(oy + dh))
        elif curr < self.RATIO - 0.01:
            # Taller than 16:9 — box moves vertically
            crop_h = dw / self.RATIO
            max_dy = dh - crop_h
            if max_dy <= 0:
                return (float(ox), float(oy), float(ox + dw), float(oy + dh))
            y0 = oy + max_dy * self._anchor_y
            return (float(ox), y0, float(ox + dw), y0 + crop_h)
        else:
            return (float(ox), float(oy), float(ox + dw), float(oy + dh))

    def _redraw(self):
        self.canvas.delete("all")
        if self._tk_img is None:
            self._draw_placeholder()
            return
        ox, oy = self._img_offset
        self.canvas.create_image(ox, oy, anchor="nw", image=self._tk_img)
        rect = self._get_crop_rect()
        if rect is None:
            return
        x0, y0, x1, y1 = rect
        dw, dh = self._img_disp_size
        for rx0, ry0, rx1, ry1 in _outside_rects(ox, oy, dw, dh, x0, y0, x1, y1):
            if rx1 > rx0 and ry1 > ry0:
                self.canvas.create_rectangle(
                    rx0, ry0, rx1, ry1,
                    fill="black", stipple="gray50", outline="",
                )
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=COLOR_ACCENT, width=2)

    def _on_press(self, event):
        rect = self._get_crop_rect()
        if rect is None:
            return
        x0, y0, x1, y1 = rect
        if x0 <= event.x <= x1 and y0 <= event.y <= y1:
            self._dragging = True
            self._drag_start_px = (event.x, event.y)
            self._drag_start_anchor = (self._anchor_x, self._anchor_y)
        else:
            self._jump_to(event.x, event.y)

    def _jump_to(self, mx: int, my: int):
        if self._orig_size is None:
            return
        iw, ih = self._orig_size
        ox, oy = self._img_offset
        dw, dh = self._img_disp_size
        curr = iw / ih
        if curr > self.RATIO + 0.01:
            crop_w = dh * self.RATIO
            max_dx = dw - crop_w
            if max_dx <= 0:
                return
            x0 = mx - crop_w / 2
            x0 = max(float(ox), min(float(ox + max_dx), x0))
            self._anchor_x = (x0 - ox) / max_dx
        elif curr < self.RATIO - 0.01:
            crop_h = dw / self.RATIO
            max_dy = dh - crop_h
            if max_dy <= 0:
                return
            y0 = my - crop_h / 2
            y0 = max(float(oy), min(float(oy + max_dy), y0))
            self._anchor_y = (y0 - oy) / max_dy
        self._redraw()
        if self._on_change:
            self._on_change()

    def _on_drag(self, event):
        if not self._dragging or self._orig_size is None:
            return
        iw, ih = self._orig_size
        ox, oy = self._img_offset
        dw, dh = self._img_disp_size
        curr = iw / ih
        dx = event.x - self._drag_start_px[0]
        dy = event.y - self._drag_start_px[1]
        if curr > self.RATIO + 0.01:
            crop_w = dh * self.RATIO
            max_dx = dw - crop_w
            if max_dx <= 0:
                return
            self._anchor_x = max(0.0, min(1.0,
                self._drag_start_anchor[0] + dx / max_dx))
        elif curr < self.RATIO - 0.01:
            crop_h = dw / self.RATIO
            max_dy = dh - crop_h
            if max_dy <= 0:
                return
            self._anchor_y = max(0.0, min(1.0,
                self._drag_start_anchor[1] + dy / max_dy))
        self._redraw()
        if self._on_change:
            self._on_change()

    def _on_release(self, event):
        self._dragging = False

    def get_anchor(self) -> tuple[float, float]:
        return self._anchor_x, self._anchor_y

    def reset(self):
        self._image_path = None
        self._rotation_cw = 0
        self._anchor_x = 0.5
        self._anchor_y = 0.5
        self._orig_size = None
        self._tk_img = None
        self._img_disp_size = (0, 0)
        self._img_offset = (0, 0)
        self._draw_placeholder()


class PairPreview(ctk.CTkFrame):
    """Превью фінального 32:9 результату з двох вибраних зображень."""

    PREVIEW_W = 640
    PREVIEW_H = 180

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=10, **kwargs)
        self._label = ctk.CTkLabel(self, text="", width=self.PREVIEW_W, height=self.PREVIEW_H)
        self._label.pack(padx=10, pady=10)
        self._show_placeholder()

    def _show_placeholder(self):
        img = Image.new("RGB", (self.PREVIEW_W, self.PREVIEW_H), (20, 20, 20))
        d = ImageDraw.Draw(img)
        mid = self.PREVIEW_W // 2
        d.line([(mid, 0), (mid, self.PREVIEW_H)], fill=(60, 60, 60), width=2)
        d.text((mid // 2 - 20, self.PREVIEW_H // 2 - 8), "LEFT", fill=(60, 60, 60))
        d.text((mid + mid // 2 - 24, self.PREVIEW_H // 2 - 8), "RIGHT", fill=(60, 60, 60))
        self._set(img)

    def update_preview(
        self,
        left_path: Path | None,
        right_path: Path | None,
        left_anchor=(0.5, 0.5),
        right_anchor=(0.5, 0.5),
        left_rotation: int = 0,
        right_rotation: int = 0,
    ):
        def build():
            half_w = self.PREVIEW_W // 2
            half_h = self.PREVIEW_H

            def load_half(path, anchor, rotation):
                if path is None:
                    img = Image.new("RGB", (half_w, half_h), (20, 20, 20))
                    d = ImageDraw.Draw(img)
                    d.text((half_w // 2 - 15, half_h // 2 - 8), "...", fill=(60, 60, 60))
                    return img
                from core.processor import crop_to_ratio
                img = Image.open(path).convert("RGB")
                if rotation == 90:
                    img = img.rotate(-90, expand=True)
                elif rotation == 180:
                    img = img.rotate(180, expand=True)
                elif rotation == 270:
                    img = img.rotate(90, expand=True)
                img = crop_to_ratio(img, anchor_x=anchor[0], anchor_y=anchor[1])
                img = img.resize((half_w, half_h), Image.LANCZOS)
                return img

            left = load_half(left_path, left_anchor, left_rotation)
            right = load_half(right_path, right_anchor, right_rotation)

            canvas = Image.new("RGB", (self.PREVIEW_W, self.PREVIEW_H))
            canvas.paste(left, (0, 0))
            canvas.paste(right, (half_w, 0))

            d = ImageDraw.Draw(canvas)
            d.line([(half_w, 0), (half_w, self.PREVIEW_H)], fill=(255, 255, 255, 80), width=1)

            self.after(0, lambda: self._set(canvas))

        threading.Thread(target=build, daemon=True).start()

    def _set(self, img: Image.Image):
        ctk_img = ctk.CTkImage(
            light_image=img, dark_image=img,
            size=(self.PREVIEW_W, self.PREVIEW_H),
        )
        self._label.configure(image=ctk_img)
        self._label._image = ctk_img
