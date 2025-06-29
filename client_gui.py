import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, simpledialog, scrolledtext
import threading
import os
import sys
import shutil
import client

class ClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Secure File Transfer Client")
        master.geometry("700x500")

        self.style = tb.Style("darkly")

        self.download_dir = os.getcwd()
        self.download_filename = None

        self.notebook = tb.Notebook(master, bootstyle="primary")
        self.tab_upload = tb.Frame(self.notebook)
        self.tab_download = tb.Frame(self.notebook)
        self.tab_log = tb.Frame(self.notebook)

        self.notebook.add(self.tab_upload, text="Upload")
        self.notebook.add(self.tab_download, text="Download")
        self.notebook.add(self.tab_log, text="Log")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_upload_tab()
        self.create_download_tab()
        self.create_log_tab()
        self.redirect_stdout()
        self.file_path = None

    def create_upload_tab(self):
        label = tb.Label(self.tab_upload, text="Chọn file để upload:", font=("Segoe UI", 12))
        label.pack(pady=10)

        self.label_filename = tb.Label(self.tab_upload, text="Không có file nào được chọn", bootstyle="info")
        self.label_filename.pack()

        btn_browse = tb.Button(self.tab_upload, text="Chọn file", command=self.browse_file, bootstyle="outline-secondary")
        btn_browse.pack(pady=5)

        btn_upload = tb.Button(self.tab_upload, text="Upload", command=self.threaded_upload, bootstyle="success")
        btn_upload.pack(pady=10)

    def create_download_tab(self):
        label = tb.Label(self.tab_download, text="Chọn file (chỉ để lấy tên tương ứng trên server):", font=("Segoe UI", 12))
        label.pack(pady=10)

        btn_choose_remote = tb.Button(self.tab_download, text="Chọn tên file", command=self.choose_remote_file, bootstyle="outline-secondary")
        btn_choose_remote.pack(pady=5)

        btn_folder = tb.Button(self.tab_download, text="Chọn thư mục lưu", command=self.choose_download_folder, bootstyle="outline-info")
        btn_folder.pack(pady=5)

        self.label_download_path = tb.Label(self.tab_download, text=f"Thư mục lưu: {self.download_dir}", bootstyle="info")
        self.label_download_path.pack()

        btn_download = tb.Button(self.tab_download, text="Download", command=self.threaded_download, bootstyle="primary")
        btn_download.pack(pady=10)

    def choose_remote_file(self):
        path = filedialog.askopenfilename(title="Chọn file bất kỳ để lấy tên (giống tên server)")
        if path:
            self.download_filename = os.path.basename(path)
            print(f"[CHỌN FILE] Tên file sẽ tải từ server: {self.download_filename}")

    def choose_download_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.download_dir = path
            self.label_download_path.config(text=f"Thư mục lưu: {self.download_dir}")

    def create_log_tab(self):
        self.log = scrolledtext.ScrolledText(self.tab_log, width=80, height=25, font=("Consolas", 10))
        self.log.pack(padx=10, pady=10, fill="both", expand=True)

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path = path
            self.label_filename.config(text=os.path.basename(path))

    def threaded_upload(self):
        if not self.file_path:
            messagebox.showwarning("Lỗi", "Vui lòng chọn file để upload")
            return
        threading.Thread(target=self.upload_file, daemon=True).start()

    def threaded_download(self):
        if not self.download_filename:
            messagebox.showwarning("Lỗi", "Vui lòng chọn file (tên) để tải từ server")
            return
        threading.Thread(target=self.download_file, args=(self.download_filename,), daemon=True).start()

    def upload_file(self):
        try:
            client.upload(self.file_path)
        except Exception as e:
            print(f"[EXCEPTION] {e}")

    def download_file(self, filename):
        try:
            client.download(filename)
            downloaded_file = f"downloaded_{filename}"
            src = os.path.join(os.getcwd(), downloaded_file)

            # hỏi người dùng muốn đổi tên file lưu lại không
            new_name = simpledialog.askstring("Lưu với tên mới", "Nhập tên mới cho file (hoặc để trống để giữ nguyên):")
            final_name = new_name.strip() if new_name else downloaded_file
            dest = os.path.join(self.download_dir, final_name)

            os.makedirs(self.download_dir, exist_ok=True)
            if os.path.exists(src):
                shutil.move(src, dest)
                print(f"[OK] File đã lưu tại: {dest}")
            else:
                print(f"[ERR] Không tìm thấy file: {src}")
        except Exception as e:
            print(f"[EXCEPTION] {e}")

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
