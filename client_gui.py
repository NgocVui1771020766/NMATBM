import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, scrolledtext
import threading
import os
import sys
import shutil
import client
from pathlib import Path

class ClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Secure File Transfer Client")
        master.geometry("800x600")

        self.style = tb.Style("darkly")
        self.available_themes = [
            "darkly", "flatly", "minty", "cyborg", "journal",
            "litera", "superhero", "morph", "vapor", "yeti"
        ]
        self.available_themes = [
            "darkly", "flatly", "minty", "cyborg", "journal",
            "litera", "superhero", "morph", "vapor", "yeti"
        ]
        self.current_theme = "darkly"
        self.current_theme_index = 0

        self.create_topbar(master)

        self.notebook = tb.Notebook(master, bootstyle="primary")
        self.tab_main = tb.Frame(self.notebook, padding=15)
        self.tab_log = tb.Frame(self.notebook, padding=15)

        self.notebook.add(self.tab_main, text="⬆️ Upload & ⬇️ Download")
        self.notebook.add(self.tab_log, text="📜 Log")
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.create_main_tab()
        self.create_log_tab()
        self.redirect_stdout()
        self.file_path = None
        self.download_filename = None

    def create_topbar(self, master):
        topbar = tb.Frame(master, bootstyle="dark")
        topbar.pack(fill="x", padx=15, pady=5)

        # Theme selector
        theme_label = tb.Label(topbar, text="🎨 Giao diện:", bootstyle="inverse-dark")
        theme_label.pack(side="left", padx=(0, 5))

        self.theme_combo = tb.Combobox(topbar, values=self.available_themes, state="readonly", width=15)
        self.theme_combo.set(self.current_theme)
        self.theme_combo.pack(side="left")

        apply_btn = tb.Button(topbar, text="Áp dụng", command=self.apply_selected_theme, bootstyle="info", width=26, padding=14, style="success-outline")
        apply_btn.pack(side="left", padx=10)

        # Language selector
        lang_label = tb.Label(topbar, text="🌐 Ngôn ngữ:", bootstyle="inverse-dark")
        lang_label.pack(side="left", padx=(30, 5))

        self.lang_combo = tb.Combobox(topbar, values=["🇻🇳 Vietnamese", "🇬🇧 English"], state="readonly", width=18)
        self.lang_combo.set("🇻🇳 Vietnamese")
        self.lang_combo.pack(side="left")

        lang_btn = tb.Button(topbar, text="Chọn", command=self.apply_language, bootstyle="warning")
        lang_btn.pack(side="left", padx=5)

    def apply_selected_theme(self):
        new_theme = self.theme_combo.get()
        if new_theme in self.available_themes:
            self.style.theme_use(new_theme)
            self.theme_combo.set(new_theme)
            self.current_theme = new_theme
            self.current_theme_index = self.available_themes.index(new_theme)

    def create_main_tab(self):
        left = tb.Frame(self.tab_main)
        right = tb.Frame(self.tab_main)
        left.pack(side="left", expand=True, fill="both", padx=10)
        right.pack(side="right", expand=True, fill="both", padx=10)

        # Upload section
        tb.Label(left, text="Chọn file để upload:", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 5))
        self.label_filename = tb.Label(left, text="Không có file nào được chọn", bootstyle="info")
        self.label_filename.pack(anchor="w", fill="x", padx=(0, 5))
        row = tb.Frame(left)
        row.pack(pady=10, fill="x")
        tb.Button(row, text="📂 Chọn file", command=self.browse_file, bootstyle="outline-secondary")\
            .pack(side="left", padx=5)
        tb.Button(row, text="⬆️ Upload", command=self.threaded_upload, bootstyle="success")\
            .pack(side="left", padx=5)

        # Download section
        tb.Label(right, text="Chọn file từ máy (trùng với tên đã upload):", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 5))
        btn_choose = tb.Button(right, text="📂 Chọn file", command=self.choose_filename_for_download, bootstyle="outline-secondary")
        btn_choose.pack(pady=5, anchor="w")
        btn_download = tb.Button(right, text="⬇️ Download", command=self.threaded_download, bootstyle="primary")
        btn_download.pack(pady=10, anchor="w")

        

        

    def create_log_tab(self):
        tb.Label(self.tab_log, text="📜 Nhật ký hệ thống:", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 5))
        self.log = scrolledtext.ScrolledText(self.tab_log, width=90, height=28, font=("Consolas", 10))
        self.log.pack(padx=10, pady=10, fill="both", expand=True)

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path = path
            self.label_filename.config(text=os.path.basename(path))

    def choose_filename_for_download(self):
        path = filedialog.askopenfilename(title="Chọn file cục bộ để lấy tên tải từ server")
        if path:
            self.download_filename = os.path.basename(path)
            print(f"[CHỌN FILE] Tên để tải từ server: {self.download_filename}")

    def threaded_upload(self):
        if not self.file_path:
            messagebox.showwarning("Lỗi", "Vui lòng chọn file để upload")
            return
        threading.Thread(target=self.upload_file, daemon=True).start()

    def threaded_download(self):
        if not self.download_filename:
            messagebox.showwarning("Lỗi", "Vui lòng chọn file để tải từ server")
            return
        threading.Thread(target=self.download_file, daemon=True).start()

    def upload_file(self):
        try:
            client.upload(self.file_path)
            messagebox.showinfo("Upload", f"Đã upload thành công: {os.path.basename(self.file_path)}")
            self.master.bell()
        except Exception as e:
            print(f"[EXCEPTION] {e}")

    def download_file(self):
        try:
            save_path = filedialog.asksaveasfilename(title="Chọn nơi lưu file tải về", initialfile=self.download_filename)
            if not save_path:
                print("[HỦY] Người dùng chưa chọn vị trí lưu")
                return

            filename = self.download_filename
            temp_file = Path(f"downloaded_{filename}")
            if temp_file.exists():
                temp_file.unlink()

            client.download(filename)

            if temp_file.exists():
                shutil.move(str(temp_file), save_path)
                print(f"[OK] File đã lưu tại: {save_path}")
                messagebox.showinfo("Download", f"Tải thành công: {os.path.basename(save_path)}")
                self.play_download_sound()
                os.startfile(os.path.dirname(save_path))
            else:
                print(f"[ERR] Không tìm thấy file sau khi tải: {temp_file}")

        except Exception as e:
            print(f"[EXCEPTION] {e}")

    def play_download_sound(self):
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            self.master.bell()

    def apply_language(self):
        lang = self.lang_combo.get()
        messagebox.showinfo("Thông báo", f"Bạn đã chọn ngôn ngữ: {lang} (tính năng chưa được kích hoạt hoàn chỉnh)")

    def redirect_stdout(self):
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget

            def write(self, msg):
                self.text_widget.insert("end", msg)
                self.text_widget.see("end")

            def flush(self):
                pass

        sys.stdout = StdoutRedirector(self.log)
        sys.stderr = StdoutRedirector(self.log)

if __name__ == "__main__":
    app = tb.Window(themename="darkly")
    gui = ClientGUI(app)
    app.mainloop()
