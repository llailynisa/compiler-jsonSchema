"""Antarmuka desktop sederhana untuk compiler JSON Schema ke Java."""

from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from main import run


class CompilerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JSON Schema to Java")
        self.geometry("720x480")
        self.minsize(560, 360)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value="output")

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=1)

        ttk.Label(root, text="File JSON Schema").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(root, textvariable=self.input_path).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Button(root, text="Pilih…", command=self.choose_input).grid(row=0, column=2, padx=(8, 0), pady=6)

        ttk.Label(root, text="Folder keluaran").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(root, textvariable=self.output_path).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(root, text="Pilih…", command=self.choose_output).grid(row=1, column=2, padx=(8, 0), pady=6)

        self.compile_button = ttk.Button(root, text="Compile ke Java", command=self.compile)
        self.compile_button.grid(row=2, column=1, sticky="e", pady=(12, 8))

        ttk.Label(root, text="File Java hasil generate").grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 4))
        result = ttk.Panedwindow(root, orient="horizontal")
        result.grid(row=4, column=0, columnspan=3, sticky="nsew")
        files_frame = ttk.Frame(result, padding=(0, 0, 8, 0))
        code_frame = ttk.Frame(result)
        result.add(files_frame, weight=1)
        result.add(code_frame, weight=4)

        self.files = tk.Listbox(files_frame, exportselection=False, width=24)
        self.files.pack(fill="both", expand=True)
        self.files.bind("<<ListboxSelect>>", self.show_selected_file)
        self.code = tk.Text(code_frame, wrap="none", state="disabled", font=("Consolas", 10))
        self.code.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(code_frame, orient="vertical", command=self.code.yview)
        scrollbar.pack(side="right", fill="y")
        self.code.configure(yscrollcommand=scrollbar.set)
        self.generated_files = []

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Pilih file JSON Schema",
            filetypes=(("JSON", "*.json"), ("Semua file", "*.*")),
        )
        if path:
            self.input_path.set(path)

    def choose_output(self):
        path = filedialog.askdirectory(title="Pilih folder keluaran")
        if path:
            self.output_path.set(path)

    def show_selected_file(self, _event=None):
        selection = self.files.curselection()
        if not selection:
            return
        path = self.generated_files[selection[0]]
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            content = f"Gagal membaca {path}: {exc}"
        self.code.configure(state="normal")
        self.code.delete("1.0", "end")
        self.code.insert("1.0", content)
        self.code.configure(state="disabled")

    def compile(self):
        source = self.input_path.get().strip()
        destination = self.output_path.get().strip() or "output"
        if not source:
            messagebox.showwarning("File belum dipilih", "Pilih file JSON Schema terlebih dahulu.")
            return
        if not Path(source).is_file():
            messagebox.showerror("File tidak ditemukan", source)
            return

        self.compile_button.configure(state="disabled")
        try:
            output = StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                status = run([source, "--output", destination])
            self.files.delete(0, "end")
            self.generated_files = []
            self.code.configure(state="normal")
            self.code.delete("1.0", "end")
            self.code.configure(state="disabled")
            if status == 0:
                for line in output.getvalue().splitlines():
                    if line.startswith("Dibuat: "):
                        path = Path(line.removeprefix("Dibuat: ").strip())
                        self.generated_files.append(path)
                        self.files.insert("end", path.name)
                if self.generated_files:
                    self.files.selection_set(0)
                    self.show_selected_file()
            else:
                messagebox.showerror("Compile gagal", output.getvalue().strip() or f"Kode error {status}")
        except Exception as exc:
            messagebox.showerror("Kesalahan", str(exc))
        finally:
            self.compile_button.configure(state="normal")


if __name__ == "__main__":
    CompilerGUI().mainloop()
