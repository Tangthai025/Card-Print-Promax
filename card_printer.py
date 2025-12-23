import sys
import os
import time
import tempfile
import shutil
import requests
from threading import Thread

# ใช้ PIL (Pillow) สำหรับจัดการรูปภาพ
from PIL import Image

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton, QFileDialog, 
                             QFrame, QMessageBox, QComboBox, QSpinBox, QTabWidget,
                             QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QMenu)
# เอา QKeySequence ออกจาก QtCore
from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSignal, QThread, QMimeData, QPoint 
# ย้าย QKeySequence มาใส่ใน QtGui และเพิ่ม QDrag
from PyQt6.QtGui import (QPainter, QColor, QPen, QPixmap, QFont, QDragEnterEvent, 
                         QDropEvent, QIcon, QAction, QKeySequence, QDrag) 
from fpdf import FPDF

# ================= WORKER THREADS (API & Download) =================

class APIWorker(QThread):
    search_finished = pyqtSignal(list)
    def __init__(self, query):
        super().__init__()
        self.query = query
    def run(self):
        try:
            url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
            params = {"fname": self.query}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200: self.search_finished.emit(r.json().get("data", []))
            else: self.search_finished.emit([])
        except: self.search_finished.emit([])

class ImageDownloadWorker(QThread):
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)
    def __init__(self, url, temp_dir, name):
        super().__init__()
        self.url, self.temp_dir, self.name = url, temp_dir, name
    def run(self):
        try:
            r = requests.get(self.url, timeout=15)
            if r.status_code == 200:
                safe = "".join([c for c in self.name if c.isalnum()]) or "card"
                path = os.path.join(self.temp_dir, f"{safe}.jpg")
                with open(path, 'wb') as f: f.write(r.content)
                self.download_finished.emit(path)
            else: self.download_error.emit(str(r.status_code))
        except Exception as e: self.download_error.emit(str(e))

class DeckImportWorker(QThread):
    progress_update = pyqtSignal(int, int)
    image_ready = pyqtSignal(str)
    finished_import = pyqtSignal()
    def __init__(self, id_list, temp_dir):
        super().__init__()
        self.id_list, self.temp_dir = id_list, temp_dir
    def run(self):
        total = len(self.id_list)
        for i, cid in enumerate(self.id_list):
            try:
                r = requests.get(f"https://db.ygoprodeck.com/api/v7/cardinfo.php?id={cid}", timeout=5)
                if r.status_code == 200:
                    img_url = r.json()["data"][0]["card_images"][0]["image_url"]
                    ir = requests.get(img_url, timeout=10)
                    if ir.status_code == 200:
                        path = os.path.join(self.temp_dir, f"{cid}.jpg")
                        with open(path, 'wb') as f: f.write(ir.content)
                        self.image_ready.emit(path)
            except: pass
            self.progress_update.emit(i+1, total)
        self.finished_import.emit()

# ================= UI WIDGETS =================

class CardSlot(QWidget):
    def __init__(self, slot_index, parent_preview):
        super().__init__(parent_preview)
        self.slot_index = slot_index
        self.parent_preview = parent_preview
        self.image_path = None
        self.drag_start_pos = None # สำหรับจำจุดเริ่มลาก
        
        # เพิ่ม Focus Policy เพื่อให้รับ Keyboard Event ได้
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus) 
        self.setAcceptDrops(True)
        
        # --- UI Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(0, 25, 0, 0) # เว้นข้างบนไว้ใส่ตัวเลข #1

        # ปุ่ม Add Image
        self.btn_add = QPushButton("Add Image")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedSize(90, 35)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #0ea5e9; 
                color: white; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #0284c7;
            }
            QPushButton:hover { background-color: #38bdf8; }
        """)
        self.btn_add.clicked.connect(self.on_click_add)
        self.layout.addWidget(self.btn_add)

        # ปุ่ม ลบ (ซ่อนอยู่)
        self.btn_remove = QPushButton("✖", self)
        self.btn_remove.setFixedSize(24, 24)
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #ef4444; color: white; 
                border-radius: 12px; border: 2px solid white; font-weight: bold;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_remove.clicked.connect(self.remove_image)
        self.btn_remove.hide()

    def resizeEvent(self, event):
        self.btn_remove.move(self.width()-30, 5) 
        super().resizeEvent(event)

    def on_click_add(self):
        self.setFocus()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path: self.parent_preview.app.update_single_slot(self.slot_index, file_path)

    def remove_image(self):
        self.parent_preview.app.update_single_slot(self.slot_index, None)
        self.setFocus()

    def update_image(self, path):
        self.image_path = path
        if path and os.path.exists(path):
            self.btn_add.hide()
            self.btn_remove.show()
        else:
            self.btn_add.show()
            self.btn_remove.hide()
        self.update()

    # --- Mouse Events (Start Dragging) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus() # คลิกซ้ายเพื่อเลือก (Focus)
            self.drag_start_pos = event.pos() # จำตำแหน่งคลิก
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # ตรวจสอบว่ากำลังกดคลิกซ้ายและลากหรือไม่
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if not self.drag_start_pos: return
        
        # เช็คระยะทางว่าลากไปไกลพอที่จะถือว่าเป็น Drag หรือไม่ (ป้องกันมือลั่น)
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        # เริ่มต้นการ Drag
        drag = QDrag(self)
        mime = QMimeData()
        
        # ส่งข้อมูล Index ของตัวเองไป (รูปแบบ: "swap:เลขIndex")
        mime.setText(f"swap:{self.slot_index}")
        drag.setMimeData(mime)

        # สร้างภาพ Ghost ติดเมาส์
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        # วาดหน้าตาปัจจุบันของ Widget ลงไปใน Pixmap (รวมปุ่ม รวมรูป ถ้ามี)
        self.render(painter)
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos()) # จุดจับคือจุดที่เมาส์อยู่

        # เริ่ม Drag (DropAction จะถูกจัดการใน dropEvent)
        drag.exec(Qt.DropAction.MoveAction)

    # --- Drag & Drop Events (Accept Drop) ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        m = event.mimeData()
        # รับทั้งไฟล์จากข้างนอก และคำสั่ง swap จากข้างใน
        if m.hasUrls() or (m.hasText() and m.text().startswith("swap:")):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        m = event.mimeData()
        
        # กรณี 1: สลับช่อง (Internal Swap)
        if m.hasText() and m.text().startswith("swap:"):
            try:
                source_idx = int(m.text().split(":")[1])
                target_idx = self.slot_index
                # เรียกฟังก์ชันสลับใน Main App
                self.parent_preview.app.swap_slots(source_idx, target_idx)
                event.accept()
                self.setFocus()
            except: pass

        # กรณี 2: ลากไฟล์มาจาก Windows Explorer
        elif m.hasUrls():
            file_path = m.urls()[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                self.parent_preview.app.update_single_slot(self.slot_index, file_path)
                event.accept()
                self.setFocus()

    # --- Context Menu (คลิกขวา) ---
    def contextMenuEvent(self, event):
        self.setFocus()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #333; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background: #ec4899; }
            QMenu::item:disabled { color: #555; }
        """)
        
        action_copy = menu.addAction("Copy (Ctrl+C)")
        action_copy.triggered.connect(self.copy_image)
        action_copy.setEnabled(bool(self.image_path))

        action_paste = menu.addAction("Paste (Ctrl+V)")
        action_paste.triggered.connect(self.paste_image)

        menu.addSeparator()
        
        action_del = menu.addAction("Delete (Del)")
        action_del.triggered.connect(self.remove_image)
        action_del.setEnabled(bool(self.image_path))

        menu.exec(event.globalPos())

    # --- Keyboard Events (Ctrl+C, Ctrl+V, Delete) ---
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_image()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_image()
        elif event.key() == Qt.Key.Key_Delete:
            self.remove_image()
        else:
            super().keyPressEvent(event)

    # --- Copy / Paste Logic ---
    def copy_image(self):
        if self.image_path and os.path.exists(self.image_path):
            QApplication.clipboard().setText(self.image_path)

    def paste_image(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        path = None

        # กรณี 1: ก๊อปไฟล์มาจาก Windows Explorer
        if mime_data.hasUrls():
            local_file = mime_data.urls()[0].toLocalFile()
            if local_file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                path = local_file
        
        # กรณี 2: ก๊อป Path มาจากในโปรแกรม (Text)
        elif mime_data.hasText():
            text = mime_data.text()
            # ตัด prefix file:/// ออกถ้ามี
            if text.startswith("file:///"):
                text = text[8:]
            if os.path.exists(text):
                path = text
        
        if path:
            self.parent_preview.app.update_single_slot(self.slot_index, path)

    # --- Drawing ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        # Highlight Selected (กรอบทอง)
        if self.hasFocus():
            painter.setPen(QPen(QColor("#fbbf24"), 3)) # สีทอง
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(1,1,-1,-1))

        if self.image_path and os.path.exists(self.image_path):
            # วาดรูป
            painter.drawPixmap(rect, QPixmap(self.image_path))
            
            # เส้นขอบบางๆ
            painter.setPen(QPen(QColor(0,0,0,50), 1))
            painter.drawRect(rect.adjusted(0,0,-1,-1))
            
            # ป้ายเลขมุมขวาล่าง
            num = (self.parent_preview.app.current_page * 9) + self.slot_index + 1
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect.width()-35, rect.height()-22, 35, 22), 4, 4)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(rect.width()-35, rect.height()-22, 35, 22), Qt.AlignmentFlag.AlignCenter, f"#{num}")
        else:
            # วาดเส้นประ
            painter.setPen(QPen(QColor("#798b8d"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(1,1,-1,-1))
            
            # เลขตัวใหญ่ด้านบน
            painter.setPen(QColor("#1e1f1f"))
            painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            text_rect = QRectF(0, 5, rect.width(), 30)
            num = (self.parent_preview.app.current_page * 9) + self.slot_index + 1
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"#{num}")

# --- Search Tab ---
class YGOSearchTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.temp_dir = main_app.temp_dir
        self.download_threads = [] 
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        search_layout = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Enter card name...")
        self.inp_search.setStyleSheet("padding: 8px; border-radius: 4px; background: #111; color: white; border: 1px solid #555;")
        self.inp_search.returnPressed.connect(self.start_search)
        
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(40, 35)
        self.btn_search.setStyleSheet("background-color: #ec4899; border-radius: 4px;")
        self.btn_search.clicked.connect(self.start_search)
        
        search_layout.addWidget(self.inp_search)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #0ea5e9; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(60, 87))
        self.list_widget.setStyleSheet("QListWidget { background-color: #222; border: none; } QListWidget::item { padding: 5px; } QListWidget::item:selected { background-color: #ec4899; }")
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

    def start_search(self):
        query = self.inp_search.text().strip()
        if not query: return
        self.list_widget.clear()
        self.btn_search.setEnabled(False)
        self.lbl_status.setText(f"Searching '{query}'...")
        
        self.worker = APIWorker(query)
        self.worker.search_finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_finished(self, cards):
        self.btn_search.setEnabled(True)
        self.lbl_status.setText("")
        if not cards:
            self.lbl_status.setText("No cards found.")
            return

        for card in cards[:30]:
            name = card.get("name", "Unknown")
            images = card.get("card_images", [])
            if images:
                img_url_small = images[0].get("image_url_small")
                img_url_big = images[0].get("image_url")
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, img_url_big) 
                try:
                    data = requests.get(img_url_small, timeout=2).content
                    pixmap = QPixmap()
                    pixmap.loadFromData(data)
                    item.setIcon(QIcon(pixmap))
                except: pass
                self.list_widget.addItem(item)

    def on_item_clicked(self, item):
        big_url = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        self.lbl_status.setText(f"Downloading: {name}...")
        self.list_widget.setEnabled(False)
        
        downloader = ImageDownloadWorker(big_url, self.temp_dir, name)
        downloader.download_finished.connect(self.on_download_success)
        downloader.download_error.connect(self.on_download_error)
        self.download_threads.append(downloader)
        downloader.start()

    def on_download_success(self, file_path):
        self.lbl_status.setText("Download Complete!")
        self.list_widget.setEnabled(True)
        success = self.main_app.add_image_to_next_free_slot(file_path)
        if not success:
             QMessageBox.warning(self, "Page Full", "No empty slots on this page.")

    def on_download_error(self, error_msg):
        self.lbl_status.setText(f"Error: {error_msg}")
        self.list_widget.setEnabled(True)

# --- Main App ---
class CardPrinterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Card Copy Promax")
        self.setGeometry(100, 100, 1300, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.temp_dir = tempfile.mkdtemp()
        self.images_data = {} 
        self.current_page = 0 
        self.max_page_reached = 0
        self.import_worker = None
        
        self.config = {
            'card_w': 59, 'card_h': 86, 'gap': 4, 
            'margin_top': 15, 'margin_left': 12,
            'paper_w': 210, 'paper_h': 297
        }
        
        self.card_presets = {
            "Custom": (0, 0),
            "Vanguard/YGO (59x86)": (59, 86),
            "Pokemon/MTG (63x88)": (63, 88),
        }
        self.paper_presets = {
            "A4": (210, 297), "A3": (297, 420), "Letter": (215.9, 279.4)
        }
        self.controls = {} 
        self.init_ui()

    def closeEvent(self, event):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().closeEvent(event)

    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # Left Panel
        left_container = QWidget()
        left_container.setFixedWidth(400)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0,0,0,0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; }
            QTabBar::tab { background: #2d2d2d; color: #aaa; padding: 10px 20px; }
            QTabBar::tab:selected { background: #374151; color: #ec4899; font-weight: bold; }
        """)
        
        self.tab_settings = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "⚙️ Settings")

        self.tab_search = YGOSearchTab(self)
        self.tabs.addTab(self.tab_search, "🐉 Search")

        left_layout.addWidget(self.tabs)
        main_layout.addWidget(left_container)

        # Right Panel
        self.preview_area = PreviewWidget(self)
        
        container = QWidget()
        container.setLayout(main_layout)
        main_layout.addWidget(self.preview_area)
        self.setCentralWidget(container)
        self.update_ui_state()

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        
        title = QLabel("Design & Print")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("margin-bottom: 5px; color: #ec4899;")
        layout.addWidget(title)

        # Configs
        layout.addWidget(QLabel("Paper Size:", styleSheet="color: #aaa;"))
        self.paper_combo = QComboBox()
        self.paper_combo.addItems(self.paper_presets.keys())
        self.paper_combo.setStyleSheet(self.combo_style())
        self.paper_combo.currentTextChanged.connect(self.apply_paper_preset)
        layout.addWidget(self.paper_combo)
        
        layout.addSpacing(5)

        layout.addWidget(QLabel("Card Preset:", styleSheet="color: #aaa;"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.card_presets.keys())
        self.preset_combo.setCurrentText("Vanguard/YGO (59x86)")
        self.preset_combo.setStyleSheet(self.combo_style())
        self.preset_combo.currentTextChanged.connect(self.apply_card_preset)
        layout.addWidget(self.preset_combo)

        layout.addSpacing(10)

        # Slider Group
        self.create_control_row(layout, "Width (mm)", 'card_w', 40, 100)
        self.create_control_row(layout, "Height (mm)", 'card_h', 60, 150)
        self.create_control_row(layout, "Gap (mm)", 'gap', 0, 20)
        self.create_control_row(layout, "Margin Top", 'margin_top', 0, 100)
        self.create_control_row(layout, "Margin Left", 'margin_left', 0, 100)
        
        layout.addSpacing(15)
        
        # Action Buttons
        self.btn_ydk = QPushButton("📂 Import .ydk Deck")
        self.btn_ydk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ydk.setStyleSheet("background-color: #f59e0b; color: black; padding: 10px; border-radius: 6px; font-weight: bold;")
        self.btn_ydk.clicked.connect(self.import_ydk_file)
        layout.addWidget(self.btn_ydk)

        # Progress Bar for Import
        self.pbar = QProgressBar()
        self.pbar.setStyleSheet("QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; } QProgressBar::chunk { background-color: #f59e0b; }")
        self.pbar.hide()
        layout.addWidget(self.pbar)

        self.btn_upload = QPushButton("🖼️ Bulk Images")
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.setStyleSheet("background-color: #374151; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        self.btn_upload.clicked.connect(self.bulk_upload)
        layout.addWidget(self.btn_upload)
        
        layout.addStretch()

        # Pagination
        page_group = QFrame()
        page_group.setStyleSheet("background-color: #1f2937; border-radius: 8px; padding: 5px;")
        page_layout = QVBoxLayout(page_group)
        
        self.btn_add_page = QPushButton("Add New Page")
        self.btn_add_page.setStyleSheet("background-color: #059669; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_add_page.clicked.connect(self.add_new_page)
        page_layout.addWidget(self.btn_add_page)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_prev.clicked.connect(lambda: self.change_page(-1))
        self.lbl_page = QLabel("Page 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next = QPushButton("▶")
        self.btn_next.clicked.connect(lambda: self.change_page(1))
        
        for btn in [self.btn_prev, self.btn_next]:
            btn.setFixedSize(40, 30)
            btn.setStyleSheet("background-color: #4b5563;")

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_page)
        nav_layout.addWidget(self.btn_next)
        page_layout.addLayout(nav_layout)
        layout.addWidget(page_group)
        
        layout.addSpacing(10)

        self.btn_export = QPushButton("📄 Export PDF")
        self.btn_export.setStyleSheet("background-color: #8b5cf6; color: white; padding: 15px; font-weight: bold; font-size: 16px; border-radius: 8px;")
        self.btn_export.clicked.connect(self.generate_pdf)
        layout.addWidget(self.btn_export)

    def combo_style(self):
        return """
            QComboBox { background-color: #374151; border: 1px solid #4b5563; border-radius: 4px; padding: 5px; color: white; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #374151; color: white; selection-background-color: #0ea5e9; }
        """

    def create_control_row(self, layout, label_text, key, min_v, max_v):
        wrapper = QWidget()
        l = QVBoxLayout(wrapper)
        l.setContentsMargins(0,0,0,5)
        top = QHBoxLayout()
        top.addWidget(QLabel(label_text, styleSheet="color: #d1d5db;"))
        spinbox = QSpinBox()
        spinbox.setRange(min_v, max_v)
        spinbox.setValue(int(self.config[key]))
        spinbox.setFixedWidth(70)
        spinbox.setStyleSheet("QSpinBox { background-color: #111; color: #0ea5e9; font-weight: bold; border: 1px solid #444; border-radius: 4px; padding: 2px; }")
        top.addStretch()
        top.addWidget(spinbox)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(int(self.config[key]))
        
        def on_spin_change(val):
            slider.setValue(val)
            self.update_config(key, val)
        def on_slider_change(val):
            spinbox.setValue(val)
            self.update_config(key, val)
            if key in ['card_w', 'card_h']:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentText("Custom")
                self.preset_combo.blockSignals(False)

        spinbox.valueChanged.connect(on_spin_change)
        slider.valueChanged.connect(on_slider_change)
        l.addLayout(top)
        l.addWidget(slider)
        layout.addWidget(wrapper)
        self.controls[key] = {'spin': spinbox, 'slider': slider}

    def update_config(self, key, value):
        self.config[key] = value
        self.preview_area.refresh_layout()

    def apply_card_preset(self, text):
        if text == "Custom": return
        w, h = self.card_presets[text]
        self.controls['card_w']['spin'].setValue(w)
        self.controls['card_h']['spin'].setValue(h)

    def apply_paper_preset(self, text):
        w, h = self.paper_presets[text]
        self.config['paper_w'] = w
        self.config['paper_h'] = h
        self.preview_area.refresh_layout()

    # --- YDK Import Logic ---
    def import_ydk_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Deck", "", "YGO Deck (*.ydk)")
        if not path: return

        # Parse ID from file
        ids = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line.isdigit():
                        ids.append(line)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Read failed: {e}")
            return

        if not ids:
            QMessageBox.warning(self, "Empty", "No card IDs found in this file.")
            return

        # Start Import Worker
        self.btn_ydk.setEnabled(False)
        self.pbar.show()
        self.pbar.setValue(0)
        
        self.import_worker = DeckImportWorker(ids, self.temp_dir)
        self.import_worker.progress_update.connect(self.on_import_progress)
        self.import_worker.image_ready.connect(self.add_image_to_next_free_slot)
        self.import_worker.finished_import.connect(self.on_import_finished)
        self.import_worker.start()

    def on_import_progress(self, current, total):
        perc = int((current / total) * 100)
        self.pbar.setValue(perc)
        self.pbar.setFormat(f"Downloading... {current}/{total}")

    def on_import_finished(self):
        self.btn_ydk.setEnabled(True)
        self.pbar.hide()
        QMessageBox.information(self, "Success", "Deck imported successfully!")

    # --- Common Logic ---
    def add_image_to_next_free_slot(self, file_path):
        start_idx = self.current_page * 9
        for i in range(9):
            idx = start_idx + i
            if idx not in self.images_data:
                self.update_single_slot(i, file_path)
                return True
        
        # ถ้าหน้าเต็ม ให้เปิดหน้าใหม่แล้วใส่เลย
        self.add_new_page()
        return self.add_image_to_next_free_slot(file_path)

    def update_single_slot(self, slot_idx_on_page, path):
        global_idx = (self.current_page * 9) + slot_idx_on_page
        if path is None:
            if global_idx in self.images_data: del self.images_data[global_idx]
        else:
            self.images_data[global_idx] = path
        self.preview_area.refresh_content()

    # --- SWAP LOGIC (NEW) ---
    def swap_slots(self, source_slot_idx, target_slot_idx):
        if source_slot_idx == target_slot_idx: return
        
        # คำนวณ Global Index (รวมหน้าปัจจุบันเข้าไปด้วย)
        page_offset = self.current_page * 9
        global_src = page_offset + source_slot_idx
        global_dest = page_offset + target_slot_idx
        
        # ดึงข้อมูลรูป (ถ้าไม่มีจะได้ None)
        src_img = self.images_data.get(global_src)
        dest_img = self.images_data.get(global_dest)
        
        # สลับข้อมูล
        if src_img: self.images_data[global_dest] = src_img
        elif global_dest in self.images_data: del self.images_data[global_dest]
            
        if dest_img: self.images_data[global_src] = dest_img
        elif global_src in self.images_data: del self.images_data[global_src]
            
        # รีเฟรชหน้าจอ
        self.preview_area.refresh_content()

    def bulk_upload(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg *.jpeg)")
        if files:
            for f in files:
                self.add_image_to_next_free_slot(f)
            self.update_ui_state()

    def add_new_page(self):
        self.max_page_reached += 1
        self.current_page = self.max_page_reached
        self.update_ui_state()
        self.preview_area.refresh_content()

    def change_page(self, direction):
        new_page = self.current_page + direction
        if 0 <= new_page <= self.max_page_reached:
            self.current_page = new_page
            self.update_ui_state()
            self.preview_area.refresh_content()

    def update_ui_state(self):
        real_max_page = 0
        if self.images_data:
            real_max_page = max(self.images_data.keys()) // 9
        if real_max_page > self.max_page_reached:
            self.max_page_reached = real_max_page

        self.lbl_page.setText(f"Page {self.current_page + 1}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < self.max_page_reached)

    def generate_pdf(self):
        if not self.images_data:
            QMessageBox.warning(self, "Empty", "No images placed.")
            return

        temp_pdf_dir = tempfile.mkdtemp()
        try:
            pw = self.config['paper_w']
            ph = self.config['paper_h']
            
            pdf = FPDF('P', 'mm', (pw, ph))
            pdf.set_auto_page_break(False)
            pdf.set_compression(False)

            max_idx = max(self.images_data.keys())
            total_pdf_pages = (max_idx // 9) + 1

            for p in range(total_pdf_pages):
                pdf.add_page()
                for s in range(9):
                    g_idx = (p * 9) + s
                    pos = self.calculate_pos(s)
                    
                    if g_idx in self.images_data:
                        path = self.images_data[g_idx]
                        hq_path = self.process_image(path, temp_pdf_dir, g_idx)
                        if hq_path:
                            pdf.image(hq_path, x=pos['x'], y=pos['y'], w=self.config['card_w'], h=self.config['card_h'])
                    
                    pdf.set_line_width(0.1)
                    pdf.set_draw_color(200, 200, 200)
                    pdf.rect(pos['x'], pos['y'], self.config['card_w'], self.config['card_h'])

            save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "Deck.pdf", "PDF (*.pdf)")
            if save_path:
                pdf.output(save_path)
                QMessageBox.information(self, "Done", "PDF Exported Successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            shutil.rmtree(temp_pdf_dir, ignore_errors=True)

    def process_image(self, path, temp_dir, idx):
        try:
            img = Image.open(path)
            if img.mode != 'RGB': img = img.convert('RGB')
            w_px = int((self.config['card_w']/25.4)*300)
            h_px = int((self.config['card_h']/25.4)*300)
            img = img.resize((w_px, h_px), Image.Resampling.LANCZOS)
            out = os.path.join(temp_dir, f"{idx}.jpg")
            img.save(out, quality=100, subsampling=0)
            return out
        except: return None

    def calculate_pos(self, slot_idx):
        c = slot_idx % 3
        r = slot_idx // 3
        return {
            'x': self.config['margin_left'] + (c * (self.config['card_w'] + self.config['gap'])),
            'y': self.config['margin_top'] + (r * (self.config['card_h'] + self.config['gap']))
        }

class PreviewWidget(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setStyleSheet("background-color: #111;")
        self.slots = [CardSlot(i, self) for i in range(9)]

    def resizeEvent(self, event):
        self.refresh_layout()

    def refresh_layout(self):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        
        cfg = self.app.config
        paper_ratio = cfg['paper_w'] / cfg['paper_h']
        view_ratio = w / h
        margin_padding = 40
        
        if view_ratio > paper_ratio:
            display_h = h - margin_padding
            scale = display_h / cfg['paper_h']
        else:
            display_w = w - margin_padding
            scale = display_w / cfg['paper_w']
            
        paper_pixel_w = cfg['paper_w'] * scale
        paper_pixel_h = cfg['paper_h'] * scale
        
        start_x = (w - paper_pixel_w) / 2
        start_y = (h - paper_pixel_h) / 2
        
        for i, slot in enumerate(self.slots):
            c = i % 3
            r = i // 3
            mm_x = cfg['margin_left'] + (c * (cfg['card_w'] + cfg['gap']))
            mm_y = cfg['margin_top'] + (r * (cfg['card_h'] + cfg['gap']))
            
            slot.setGeometry(
                int(start_x + (mm_x * scale)), 
                int(start_y + (mm_y * scale)), 
                int(cfg['card_w'] * scale), 
                int(cfg['card_h'] * scale)
            )
            
        self.draw_params = {'x': start_x, 'y': start_y, 'w': paper_pixel_w, 'h': paper_pixel_h}
        self.update()

    def refresh_content(self):
        base_idx = self.app.current_page * 9
        for i, slot in enumerate(self.slots):
            slot.update_image(self.app.images_data.get(base_idx + i))
            slot.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if hasattr(self, 'draw_params'):
            p = self.draw_params
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(p['x'], p['y'], p['w'], p['h']))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CardPrinterApp()
    window.show()
    sys.exit(app.exec())