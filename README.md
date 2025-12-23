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

---
<a name="คำอธิบายภาษาไทย"></a>
## 🇹🇭 คำอธิบายภาษาไทย

**Card Print Promax** คือแอปพลิเคชันบนเดสก์ท็อปที่ทรงพลังและใช้งานง่าย ออกแบบมาเพื่อผู้ชื่นชอบการ์ดเกม (TCG) โดยเฉพาะ ช่วยให้คุณจัดรูปแบบ จัดระเบียบ และพิมพ์การ์ด Proxy หรือเด็คสำหรับทดสอบเล่นได้ง่ายๆ พัฒนาด้วย **Python** และ **PyQt6**

### ✨ ฟีเจอร์หลัก

* **🎴 รองรับหลายเกม:** มีค่า Preset สำหรับ **Yu-Gi-Oh! / Vanguard** (ไซส์เล็ก) และ **Pokemon / MTG** (ไซส์มาตรฐาน)
* **🔍 ค้นหาการ์ดในตัว:** ค้นหาและดาวน์โหลดรูปการ์ดได้โดยตรงจาก **YGOPRODeck API** ภายในแอป
* **📂 นำเข้า Deck:** รองรับไฟล์ **.ydk** อย่างสมบูรณ์ เพียงนำเข้ารายชื่อเด็คของคุณ แล้วแอปจะดาวน์โหลดรูปภาพทั้งหมดให้อัตโนมัติ
* **🖱️ ระบบลากวาง (Drag & Drop):**
    * ลากไฟล์รูปจากคอมพิวเตอร์มาใส่ในช่อง
    * **สลับช่อง (Swap)** ได้ง่ายๆ เพียงแค่ลากการ์ดใบหนึ่งไปวางทับอีกใบ
* **📋 รองรับ Clipboard:** คัดลอก (`Ctrl+C`) และวาง (`Ctrl+V`) รูปภาพระหว่างช่อง หรือจากภายนอกได้
* **📄 ส่งออก PDF:** สร้างไฟล์ PDF คุณภาพสูง พร้อมพิมพ์บนกระดาษ A4, A3 หรือ Letter
* **⚙️ ปรับแต่งอิสระ:** ปรับขอบกระดาษ (Margin), ระยะห่าง (Gap) และขนาดการ์ดได้ตามต้องการ

### 📸 รูปตัวอย่าง

![หน้าจอหลัก](path/to/your/screenshot.png)
*(อย่าลืมเปลี่ยน `path/to/your/screenshot.png` เป็นที่อยู่ไฟล์รูปของคุณ เช่น `screenshots/main_ui.png`)*

### 🛠️ การติดตั้งและการตั้งค่า

1.  **โคลนโปรเจกต์ (Clone repository):**
    ```bash
    git clone [https://github.com/Tangthai025/Card-Print-Promax.git](https://github.com/Tangthai025/Card-Print-Promax.git)
    cd Card-Print-Promax
    ```

2.  **ติดตั้ง Library ที่จำเป็น:**
    ```bash
    pip install PyQt6 requests fpdf Pillow
    ```

3.  **รันโปรแกรม:**
    ```bash
    python card_printer.py
    ```

### 📦 การแปลงเป็นไฟล์ .exe (ทางเลือก)
หากต้องการสร้างไฟล์โปรแกรมที่รันได้เลย (Standalone executable):
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile card_printer.py
