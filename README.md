# Card Print Promax 🖨️🃏

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Status](https://img.shields.io/badge/Status-Active-success)

**[English](#english-description) | [ภาษาไทย](#คำอธิบายภาษาไทย)**

---

<a name="english-description"></a>
## 🇬🇧 English Description

**Card Print Promax** is a powerful, user-friendly desktop application designed for Trading Card Game (TCG) enthusiasts. It allows you to easily format, organize, and print custom proxy cards or playtest decks. Built with **Python** and **PyQt6**.

### ✨ Key Features

* **🎴 Multi-Game Support:** Presets for **Yu-Gi-Oh! / Vanguard** (Small size) and **Pokemon / MTG** (Standard size).
* **🔍 Built-in Card Search:** Search and download cards directly from the **YGOPRODeck API** within the app.
* **📂 Deck Import:** Fully supports **.ydk files**. Import your entire deck list, and the app will auto-download all images.
* **🖱️ Drag & Drop System:**
    * Drag images from your computer to slots.
    * **Swap slots** easily by dragging one card onto another.
* **📋 Clipboard Support:** Copy (`Ctrl+C`) and Paste (`Ctrl+V`) images between slots or from external sources.
* **📄 PDF Export:** Generates high-quality PDFs ready for printing on A4, A3, or Letter paper.
* **⚙️ Custom Layout:** Adjustable margins, gaps, and card dimensions.

### 📸 Screenshots

![Main Interface](path/to/your/screenshot.png)
*(Replace `path/to/your/screenshot.png` with your actual image file path, e.g., `screenshots/main_ui.png`)*

### 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Tangthai025/Card-Print-Promax.git](https://github.com/Tangthai025/Card-Print-Promax.git)
    cd Card-Print-Promax
    ```

2.  **Install required libraries:**
    ```bash
    pip install PyQt6 requests fpdf Pillow
    ```

3.  **Run the application:**
    ```bash
    python card_printer.py
    ```

### 📦 Building .exe (Optional)
To create a standalone executable file:
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile card_printer.py
