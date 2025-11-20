import sys
import os
import re
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt


# ---- پردازش متن ----
def extract_text_from_pdf(file_path):
    """خواندن متن از فایل PDF"""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text("text") or ""
    except Exception as e:
        print(f"خطا در خواندن {file_path}: {e}")
    return text


def normalize_persian(text):
    """نرمال‌سازی ساده‌ی متن فارسی بدون hazm"""
    # حذف نیم‌فاصله‌های اضافی
    text = re.sub(r"[\u200c\s]+", " ", text)

    # یکنواخت‌سازی حروف
    replacements = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ؤ": "و",
        "أ": "ا",
        "إ": "ا",
        "ۀ": "ه",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # حذف فاصله‌های اضافی و نویزهای متداول
    text = re.sub(r"[ـ]+", "", text)  # کشیده‌ها
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize_words(text):
    """توکن‌سازی ساده‌ی فارسی (بدون hazm)"""
    # جداسازی بر اساس فاصله و علائم نگارشی
    tokens = re.split(r"[^\w\u0600-\u06FF]+", text)
    return [t for t in tokens if t]


def make_flexible_pattern(phrase):
    """ساخت الگوی انعطاف‌پذیر برای جست‌وجوی عبارت"""
    words = phrase.split()
    flexible_space = r"[\s\u200c]*"
    pattern = flexible_space.join(map(re.escape, words))
    return pattern


# ---- رابط گرافیکی ----
class PDFAnalyzerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔍 جست‌وجوی عبارت در PDFها")
        self.setGeometry(300, 200, 500, 250)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label_folder = QLabel("📁 پوشه‌ای را که فایل‌های PDF در آن هستند انتخاب کنید:")
        layout.addWidget(self.label_folder)

        self.btn_select_folder = QPushButton("انتخاب پوشه")
        self.btn_select_folder.clicked.connect(self.select_folder)
        layout.addWidget(self.btn_select_folder)

        self.folder_path_label = QLabel("هیچ پوشه‌ای انتخاب نشده است.")
        self.folder_path_label.setStyleSheet("color: gray;")
        layout.addWidget(self.folder_path_label)

        self.label_word = QLabel("🔎 عبارت مورد نظر را وارد کنید:")
        layout.addWidget(self.label_word)

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("مثلاً: هوش مصنوعی")
        layout.addWidget(self.word_input)

        self.btn_analyze = QPushButton("شروع تحلیل")
        self.btn_analyze.clicked.connect(self.analyze)
        layout.addWidget(self.btn_analyze)

        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه‌ی PDF")
        if folder:
            self.folder_path_label.setText(folder)
            self.folder_path_label.setStyleSheet("color: green;")
        else:
            self.folder_path_label.setText("هیچ پوشه‌ای انتخاب نشده است.")
            self.folder_path_label.setStyleSheet("color: gray;")

    def analyze(self):
        folder_path = self.folder_path_label.text().strip()
        phrase = self.word_input.text().strip()

        if not folder_path or folder_path == "هیچ پوشه‌ای انتخاب نشده است.":
            QMessageBox.warning(self, "خطا", "لطفاً پوشه‌ی شامل PDFها را انتخاب کنید.")
            return

        if not phrase:
            QMessageBox.warning(self, "خطا", "لطفاً عبارت مورد نظر را وارد کنید.")
            return

        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        if not pdf_files:
            QMessageBox.warning(self, "خطا", "هیچ فایل PDF در پوشه پیدا نشد.")
            return

        phrase = normalize_persian(phrase)
        phrase = re.sub(r"\s+", " ", phrase)
        pattern = make_flexible_pattern(phrase)

        results = []
        total_occurrences = 0

        for pdf in pdf_files:
            pdf_path = os.path.join(folder_path, pdf)
            text = extract_text_from_pdf(pdf_path)
            text = normalize_persian(text)

            count = len(re.findall(pattern, text))
            total_occurrences += count

            words = tokenize_words(text)
            total_words = len(words)

            results.append((pdf, total_words, count))

        self.show_results(results, phrase, total_occurrences, folder_path)

    def show_results(self, results, phrase, total_occurrences, folder_path):
        output_path = os.path.join(folder_path, "results.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"🔎 عبارت مورد بررسی: «{phrase}»\n\n")
            for pdf, total_words, count in results:
                f.write(f"{pdf}:\n")
                f.write(f"  کل کلمات: {total_words}\n")
                f.write(f"  تعداد وقوع «{phrase}»: {count}\n\n")
            f.write(f"📊 مجموع وقوع «{phrase}» در همه PDFها: {total_occurrences}\n")

        pdf_names = [r[0] for r in results]
        counts = [r[2] for r in results]

        plt.figure(figsize=(8, 5))
        plt.barh(pdf_names, counts)
        plt.title(f"تعداد وقوع «{phrase}» در هر PDF", fontname="B Nazanin")
        plt.xlabel("تعداد وقوع", fontname="B Nazanin")
        plt.ylabel("نام فایل‌ها", fontname="B Nazanin")
        plt.tight_layout()
        plt.show()

        QMessageBox.information(self, "انجام شد ✅",
                                f"تحلیل انجام شد و در فایل زیر ذخیره شد:\n\n{output_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFAnalyzerApp()
    window.show()
    sys.exit(app.exec_())
