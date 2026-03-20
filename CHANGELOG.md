# Changelog

All notable changes to this project will be documented here.

---

## [1.1.0] - 2026-03-20

### Added
- **⇄ Swap L / R button** — swaps the selected left and right images with a single click; crop anchor and rotation are preserved for each side
- **Responsive thumbnail grid** — column count now scales automatically with the width of the window instead of being fixed at 2 columns

### Changed
- App title updated to **32:9 Ultrawide Wallpaper Creator** across window title bar and header
- Thumbnail cards switched from `place()` to `pack()` layout for more stable rendering inside the scroll area
- Scroll area replaced with a native `tk.Canvas` + scrollbar implementation, reducing visual artifacts during scrolling on Windows

---

## [1.0.0] - 2026-03-16

### Initial release

- Visual thumbnail grid — browse wallpapers from a selected folder
- L / R badge assignment with auto-rotate logic (first click = left, second = right)
- Drag-to-crop 16:9 picker for each image with live anchor tracking
- Per-image 90° CW rotation (crop math updates accordingly)
- Live 32:9 preview of the combined result
- 10240×2880 JPEG output (each half: 5120×2880), adjustable quality slider (60–100)
- Custom output filename entry; auto-generates name from source stems if left empty
- Auto-creates `compiled/` subfolder inside the input folder if no output folder is set
