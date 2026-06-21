import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import subprocess
import os
import sys
import threading

def find_exiftool():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    for name in ['exiftool.exe', 'exiftool']:
        bundled = os.path.join(base, name)
        if os.path.exists(bundled):
            return bundled
    for path in os.environ.get('PATH', '').split(os.pathsep):
        for name in ['exiftool.exe', 'exiftool']:
            candidate = os.path.join(path, name)
            if os.path.exists(candidate):
                return candidate
    return None

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Metadata Embedder")
        self.root.geometry("720x640")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0efe9')

        self.csv_path = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.col_file = tk.StringVar()
        self.col_title = tk.StringVar()
        self.col_kw = tk.StringVar()
        self.col_desc = tk.StringVar()
        self.col_copy = tk.StringVar()
        self.csv_headers = []
        self.csv_rows = []
        self.running = False

        self.build_ui()
        self.check_exiftool()

    def check_exiftool(self):
        et = find_exiftool()
        if not et:
            self.log("⚠  ExifTool not found. Place exiftool.exe in the same folder as this app.", 'warn')
            self.log("   Download free from: https://exiftool.org", 'warn')
        else:
            self.log(f"✓  ExifTool ready: {et}", 'ok')

    def build_ui(self):
        BG = '#f0efe9'
        CARD = '#ffffff'
        BLUE = '#1f6fcc'

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=CARD, font=('Segoe UI', 10))
        style.configure('TCombobox', font=('Segoe UI', 10))

        # Header
        hdr = tk.Frame(self.root, bg=BLUE, padx=20, pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text="Stock Metadata Embedder", font=('Segoe UI', 14, 'bold'),
                 bg=BLUE, fg='white').pack(anchor='w')
        tk.Label(hdr, text="Batch embed IPTC + XMP metadata from CSV into JPEG, PNG, EPS, AI files",
                 font=('Segoe UI', 9), bg=BLUE, fg='#c8ddf5').pack(anchor='w')

        # Scrollable area
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        self.content = tk.Frame(canvas, bg=BG, padx=16, pady=8)
        self.content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.content, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        self.build_step1()
        self.build_step2()
        self.build_step3()
        self.build_log()

    def make_card(self, title, step_num):
        outer = tk.Frame(self.content, bg='#f0efe9', pady=5)
        outer.pack(fill='x')
        inner = tk.Frame(outer, bg='white', bd=1, relief='solid')
        inner.pack(fill='x')
        title_bar = tk.Frame(inner, bg='#f7f6f2', padx=14, pady=9)
        title_bar.pack(fill='x')
        tk.Label(title_bar, text=f"  {step_num}", font=('Segoe UI', 10, 'bold'),
                 bg='#1f6fcc', fg='white', width=3, padx=2).pack(side='left')
        tk.Label(title_bar, text=f"  {title}", font=('Segoe UI', 10, 'bold'),
                 bg='#f7f6f2', fg='#2a2a28').pack(side='left')
        tk.Frame(inner, bg='#e8e7e2', height=1).pack(fill='x')
        body = tk.Frame(inner, bg='white', padx=14, pady=12)
        body.pack(fill='x')
        return body

    def browse_row(self, parent, label, var, cmd):
        row = tk.Frame(parent, bg='white')
        row.pack(fill='x', pady=3)
        tk.Label(row, text=label, font=('Segoe UI', 9, 'bold'), bg='white',
                 fg='#5c5c58', width=14, anchor='w').pack(side='left')
        tk.Entry(row, textvariable=var, font=('Segoe UI', 9), bg='#f9f8f5',
                 relief='solid', bd=1).pack(side='left', fill='x', expand=True, padx=(0, 8))
        tk.Button(row, text='Browse…', command=cmd, font=('Segoe UI', 9, 'bold'),
                  bg='#1f6fcc', fg='white', relief='flat', padx=10, pady=4,
                  cursor='hand2', activebackground='#155ab0', activeforeground='white').pack(side='right')

    def build_step1(self):
        body = self.make_card('Load your CSV file', '1')
        self.browse_row(body, 'CSV File:', self.csv_path, self.load_csv)

    def build_step2(self):
        body = self.make_card('Map your CSV columns', '2')
        tk.Label(body, text='Column names are auto-detected. Adjust if needed.',
                 font=('Segoe UI', 9), bg='white', fg='#888884').pack(anchor='w', pady=(0, 8))
        self.col_combos = {}
        fields = [
            ('Filename *', self.col_file),
            ('Title', self.col_title),
            ('Keywords', self.col_kw),
            ('Description', self.col_desc),
            ('Copyright', self.col_copy),
        ]
        grid = tk.Frame(body, bg='white')
        grid.pack(fill='x')
        for i, (label, var) in enumerate(fields):
            col = i % 2
            row_n = i // 2
            cell = tk.Frame(grid, bg='white', padx=4, pady=4)
            cell.grid(row=row_n, column=col, sticky='ew', padx=4)
            grid.columnconfigure(col, weight=1)
            tk.Label(cell, text=label, font=('Segoe UI', 9, 'bold'),
                     bg='white', fg='#5c5c58').pack(anchor='w')
            cb = ttk.Combobox(cell, textvariable=var, state='readonly', font=('Segoe UI', 9))
            cb.pack(fill='x', pady=(2, 0))
            self.col_combos[label] = cb

    def build_step3(self):
        body = self.make_card('Select image folder & run', '3')
        self.browse_row(body, 'Image Folder:', self.folder_path, self.browse_folder)
        btn_row = tk.Frame(body, bg='white')
        btn_row.pack(fill='x', pady=(14, 4))
        self.embed_btn = tk.Button(
            btn_row, text='▶   Embed Metadata Now',
            command=self.start_embed,
            font=('Segoe UI', 11, 'bold'),
            bg='#1f6fcc', fg='white', relief='flat',
            padx=22, pady=10, cursor='hand2',
            activebackground='#155ab0', activeforeground='white')
        self.embed_btn.pack(side='left')
        self.progress = ttk.Progressbar(body, mode='determinate')
        self.progress.pack(fill='x', pady=(10, 0))
        self.prog_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                   bg='white', fg='#5c5c58')
        self.prog_label.pack(anchor='w', pady=(4, 0))

    def build_log(self):
        body = self.make_card('Activity Log', '✓')
        self.log_text = tk.Text(body, height=9, font=('Consolas', 9),
                                bg='#f5f4f0', relief='flat', state='disabled', wrap='word')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('ok', foreground='#2a7035')
        self.log_text.tag_config('warn', foreground='#7a5000')
        self.log_text.tag_config('err', foreground='#b02020')
        self.log_text.tag_config('info', foreground='#1f6fcc')
        clr = tk.Button(body, text='Clear log', command=self.clear_log,
                        font=('Segoe UI', 8), bg='#f0efe9', relief='flat',
                        fg='#888884', cursor='hand2')
        clr.pack(anchor='e', pady=(4, 0))

    def log(self, msg, tag=''):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', msg + '\n', tag)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')

    def load_csv(self):
        path = filedialog.askopenfilename(
            title='Select your metadata CSV',
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')])
        if not path:
            return
        self.csv_path.set(path)
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.csv_rows = list(reader)
                self.csv_headers = list(reader.fieldnames or [])
            self.log(f"✓  Loaded {len(self.csv_rows)} rows · {len(self.csv_headers)} columns · {os.path.basename(path)}", 'ok')
            self.update_combos()
        except Exception as e:
            messagebox.showerror('Error reading CSV', str(e))

    def update_combos(self):
        options = ['(skip)'] + self.csv_headers
        hints = {
            'Filename *': ['filename', 'file', 'name', 'image'],
            'Title': ['title'],
            'Keywords': ['keyword', 'tag', 'kw'],
            'Description': ['desc', 'caption', 'description'],
            'Copyright': ['copy', 'copyright', 'rights'],
        }
        vars_map = {
            'Filename *': self.col_file,
            'Title': self.col_title,
            'Keywords': self.col_kw,
            'Description': self.col_desc,
            'Copyright': self.col_copy,
        }
        for label, cb in self.col_combos.items():
            cb['values'] = options
            guessed = next(
                (c for h in hints.get(label, []) for c in self.csv_headers if h in c.lower()),
                '')
            vars_map[label].set(guessed or '(skip)')

    def browse_folder(self):
        path = filedialog.askdirectory(title='Select folder containing your images')
        if path:
            self.folder_path.set(path)

    def start_embed(self):
        if self.running:
            return
        et = find_exiftool()
        if not et:
            messagebox.showerror('ExifTool not found',
                'Please place exiftool.exe in the same folder as this app.\n\nDownload free from: https://exiftool.org')
            return
        if not self.csv_rows:
            messagebox.showerror('No CSV loaded', 'Please load a CSV file first.')
            return
        if not self.folder_path.get():
            messagebox.showerror('No folder selected', 'Please select the image folder.')
            return
        fc = self.col_file.get()
        if not fc or fc == '(skip)':
            messagebox.showerror('No filename column', 'Please select the filename column in Step 2.')
            return
        self.running = True
        self.embed_btn.config(state='disabled', text='Processing…')
        threading.Thread(target=self.run_embed, args=(et,), daemon=True).start()

    def run_embed(self, et):
        folder = self.folder_path.get()
        col_f = self.col_file.get()
        col_t = self.col_title.get()
        col_k = self.col_kw.get()
        col_d = self.col_desc.get()
        col_c = self.col_copy.get()

        total = len(self.csv_rows)
        ok = skipped = errors = 0

        self.root.after(0, lambda: self.progress.configure(maximum=total, value=0))

        for i, row in enumerate(self.csv_rows):
            filename = (row.get(col_f) or '').strip()
            if not filename:
                skipped += 1
                self.root.after(0, lambda n=i+1, t=total: self._update_progress(n, t))
                continue

            filepath = os.path.join(folder, filename)
            if not os.path.exists(filepath):
                self.root.after(0, lambda fn=filename: self.log(f'⚠  Not found: {fn}', 'warn'))
                skipped += 1
                self.root.after(0, lambda n=i+1, t=total: self._update_progress(n, t))
                continue

            cmd = [et, '-overwrite_original', '-codedcharacterset=UTF8']

            title = (row.get(col_t) or '').strip() if col_t and col_t != '(skip)' else ''
            kw_raw = (row.get(col_k) or '').strip() if col_k and col_k != '(skip)' else ''
            desc = (row.get(col_d) or '').strip() if col_d and col_d != '(skip)' else ''
            copy = (row.get(col_c) or '').strip() if col_c and col_c != '(skip)' else ''

            if title:
                cmd += [f'-Title={title}', f'-ObjectName={title}', f'-Headline={title}']
            if kw_raw:
                keywords = [k.strip() for k in kw_raw.replace(';', ',').split(',') if k.strip()]
                for kw in keywords:
                    cmd += [f'-Keywords={kw}', f'-Subject={kw}']
            if desc:
                cmd += [f'-Description={desc}', f'-Caption-Abstract={desc}']
            if copy:
                cmd += [f'-Copyright={copy}', f'-CopyrightNotice={copy}', f'-Rights={copy}']

            cmd.append(filepath)

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                if result.returncode == 0:
                    ok += 1
                    self.root.after(0, lambda fn=filename: self.log(f'✓  {fn}', 'ok'))
                else:
                    errors += 1
                    err = (result.stderr or result.stdout or 'Unknown error').strip()
                    self.root.after(0, lambda fn=filename, e=err: self.log(f'✗  {fn}  —  {e}', 'err'))
            except Exception as e:
                errors += 1
                self.root.after(0, lambda fn=filename, e=str(e): self.log(f'✗  {fn}  —  {e}', 'err'))

            self.root.after(0, lambda n=i+1, t=total: self._update_progress(n, t))

        summary = f'\n  Done!   ✓ {ok} embedded     ⚠ {skipped} skipped     ✗ {errors} errors\n'
        self.root.after(0, lambda: (
            self.log(summary, 'info'),
            self.embed_btn.config(state='normal', text='▶   Embed Metadata Now'),
            setattr(self, 'running', False)
        ))

    def _update_progress(self, n, total):
        self.progress.configure(value=n)
        self.prog_label.configure(text=f'{n} of {total} files processed')

if __name__ == '__main__':
    root = tk.Tk()
    try:
        root.iconbitmap(default='')
    except Exception:
        pass
    app = MetadataApp(root)
    root.mainloop()
