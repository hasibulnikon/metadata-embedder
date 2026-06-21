import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, subprocess, os, sys, threading

def find_exiftool():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    for name in ['exiftool.exe', 'exiftool']:
        b = os.path.join(base, name)
        if os.path.exists(b): return b
    for path in os.environ.get('PATH','').split(os.pathsep):
        for name in ['exiftool.exe','exiftool']:
            c = os.path.join(path, name)
            if os.path.exists(c): return c
    return None

# ── Dark theme colors ──────────────────────────────────────────────────
BG      = '#1a1a18'
BG2     = '#242422'
BG3     = '#2e2e2c'
TEXT    = '#e8e8e4'
TEXT2   = '#9a9a96'
BLUE    = '#3b8fe8'
GREEN   = '#4caf72'
GREEN2  = '#1a3d28'
RED     = '#e85c5c'
BORDER  = '#3a3a38'

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Metadata Embedder")
        self.root.geometry("720x660")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        self.csv_path   = tk.StringVar()
        self.folder_path= tk.StringVar()
        self.col_file   = tk.StringVar()
        self.col_title  = tk.StringVar()
        self.col_kw     = tk.StringVar()
        self.col_desc   = tk.StringVar()
        self.col_copy   = tk.StringVar()
        self.csv_headers= []
        self.csv_rows   = []
        self.running    = False

        self.build_ui()
        self.check_exiftool()

    def check_exiftool(self):
        et = find_exiftool()
        if not et:
            self.log("⚠  ExifTool not found. Place exiftool.exe in the same folder as this app.", 'warn')
            self.log("   Download free from: https://exiftool.org", 'warn')
        else:
            self.log(f"✓  ExifTool ready", 'ok')

    def build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TCombobox', fieldbackground=BG3, background=BG3,
                        foreground=TEXT, selectbackground=BLUE, selectforeground=TEXT,
                        arrowcolor=TEXT2)
        style.map('TCombobox', fieldbackground=[('readonly', BG3)],
                  foreground=[('readonly', TEXT)])
        style.configure('Vertical.TScrollbar', background=BG3, troughcolor=BG2,
                        arrowcolor=TEXT2, bordercolor=BORDER)

        # Header
        hdr = tk.Frame(self.root, bg=BG2, padx=20, pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text="Stock Metadata Embedder", font=('Segoe UI', 14, 'bold'),
                 bg=BG2, fg=TEXT).pack(side='left')
        # Reset button in header
        tk.Button(hdr, text='↺  Reset', command=self.reset_all,
                  font=('Segoe UI', 9, 'bold'), bg='#3a2020', fg='#e88080',
                  relief='flat', padx=12, pady=5, cursor='hand2',
                  activebackground='#4a2828', activeforeground='#ffaaaa').pack(side='right')

        tk.Label(hdr, text="Batch embed IPTC + XMP from CSV into JPEG, PNG, EPS, AI",
                 font=('Segoe UI', 9), bg=BG2, fg=TEXT2).pack(side='left', padx=(12,0))

        # Scrollable content
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        self.content = tk.Frame(canvas, bg=BG, padx=16, pady=8)
        self.content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=self.content, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1*(e.delta/120)),'units'))

        self.build_step1()
        self.build_step2()
        self.build_step3()
        self.build_log()

    def make_card(self, title, num):
        outer = tk.Frame(self.content, bg=BG, pady=5)
        outer.pack(fill='x')
        inner = tk.Frame(outer, bg=BG2, highlightbackground=BORDER, highlightthickness=1)
        inner.pack(fill='x')
        tbar = tk.Frame(inner, bg=BG3, padx=14, pady=9)
        tbar.pack(fill='x')
        tk.Label(tbar, text=f" {num} ", font=('Segoe UI', 9, 'bold'),
                 bg=BLUE, fg='white').pack(side='left')
        tk.Label(tbar, text=f"  {title}", font=('Segoe UI', 10, 'bold'),
                 bg=BG3, fg=TEXT).pack(side='left')
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x')
        body = tk.Frame(inner, bg=BG2, padx=14, pady=12)
        body.pack(fill='x')
        return body

    def browse_row(self, parent, label, var, cmd):
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill='x', pady=3)
        tk.Label(row, text=label, font=('Segoe UI', 9, 'bold'), bg=BG2,
                 fg=TEXT2, width=14, anchor='w').pack(side='left')
        tk.Entry(row, textvariable=var, font=('Segoe UI', 9),
                 bg=BG3, fg=TEXT, relief='flat', insertbackground=TEXT,
                 highlightbackground=BORDER, highlightthickness=1).pack(
                 side='left', fill='x', expand=True, padx=(0,8))
        tk.Button(row, text='Browse…', command=cmd, font=('Segoe UI', 9, 'bold'),
                  bg=BLUE, fg='white', relief='flat', padx=10, pady=4, cursor='hand2',
                  activebackground='#2a7fd4', activeforeground='white').pack(side='right')

    def build_step1(self):
        body = self.make_card('Load your CSV file', '1')
        self.browse_row(body, 'CSV File:', self.csv_path, self.load_csv)
        self.csv_info = tk.Label(body, text='', font=('Segoe UI', 9),
                                  bg=BG2, fg=TEXT2)
        self.csv_info.pack(anchor='w', pady=(6,0))

    def build_step2(self):
        body = self.make_card('Map your CSV columns', '2')
        tk.Label(body, text='Auto-detected. Adjust if needed.',
                 font=('Segoe UI', 9), bg=BG2, fg=TEXT2).pack(anchor='w', pady=(0,8))
        self.col_combos = {}
        fields = [('Filename *', self.col_file), ('Title', self.col_title),
                  ('Keywords', self.col_kw), ('Description', self.col_desc),
                  ('Copyright', self.col_copy)]
        grid = tk.Frame(body, bg=BG2)
        grid.pack(fill='x')
        for i, (label, var) in enumerate(fields):
            col = i % 2
            row_n = i // 2
            cell = tk.Frame(grid, bg=BG2, padx=4, pady=4)
            cell.grid(row=row_n, column=col, sticky='ew', padx=4)
            grid.columnconfigure(col, weight=1)
            tk.Label(cell, text=label, font=('Segoe UI', 9, 'bold'),
                     bg=BG2, fg=TEXT2).pack(anchor='w')
            cb = ttk.Combobox(cell, textvariable=var, state='readonly', font=('Segoe UI', 9))
            cb.pack(fill='x', pady=(2,0))
            self.col_combos[label] = cb

    def build_step3(self):
        body = self.make_card('Select image folder & run', '3')
        self.browse_row(body, 'Image Folder:', self.folder_path, self.browse_folder)
        btn_row = tk.Frame(body, bg=BG2)
        btn_row.pack(fill='x', pady=(14,4))
        self.embed_btn = tk.Button(btn_row, text='▶   Embed Metadata Now',
            command=self.start_embed, font=('Segoe UI', 11, 'bold'),
            bg=BLUE, fg='white', relief='flat', padx=22, pady=10, cursor='hand2',
            activebackground='#2a7fd4', activeforeground='white')
        self.embed_btn.pack(side='left')
        self.progress = ttk.Progressbar(body, mode='determinate')
        self.progress.pack(fill='x', pady=(10,0))
        self.prog_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                   bg=BG2, fg=TEXT2)
        self.prog_label.pack(anchor='w', pady=(4,0))

    def build_log(self):
        body = self.make_card('Activity Log', '✓')
        self.log_text = tk.Text(body, height=9, font=('Consolas', 9),
                                bg=BG3, fg=TEXT, relief='flat',
                                state='disabled', wrap='word',
                                insertbackground=TEXT,
                                selectbackground=BLUE)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('ok', foreground=GREEN)
        self.log_text.tag_config('warn', foreground='#f0c060')
        self.log_text.tag_config('err', foreground=RED)
        self.log_text.tag_config('info', foreground=BLUE)
        tk.Button(body, text='Clear log', command=self.clear_log,
                  font=('Segoe UI', 8), bg=BG3, fg=TEXT2,
                  relief='flat', cursor='hand2',
                  activebackground=BG2, activeforeground=TEXT).pack(anchor='e', pady=(4,0))

    def log(self, msg, tag=''):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', msg + '\n', tag)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0','end')
        self.log_text.configure(state='disabled')

    def reset_all(self):
        if self.running:
            messagebox.showwarning('Busy', 'Please wait for the current job to finish before resetting.')
            return
        if not messagebox.askyesno('Reset', 'Clear everything and start fresh?'):
            return
        self.csv_path.set('')
        self.folder_path.set('')
        self.col_file.set('')
        self.col_title.set('')
        self.col_kw.set('')
        self.col_desc.set('')
        self.col_copy.set('')
        self.csv_headers = []
        self.csv_rows = []
        self.csv_info.configure(text='')
        for cb in self.col_combos.values():
            cb['values'] = []
        self.progress.configure(value=0)
        self.prog_label.configure(text='')
        self.embed_btn.configure(state='normal', text='▶   Embed Metadata Now')
        self.clear_log()
        self.log('↺  Reset complete — ready for new batch.', 'info')

    def load_csv(self):
        path = filedialog.askopenfilename(title='Select metadata CSV',
            filetypes=[('CSV files','*.csv'),('All files','*.*')])
        if not path: return
        self.csv_path.set(path)
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.csv_rows = list(reader)
                self.csv_headers = list(reader.fieldnames or [])
            self.csv_info.configure(
                text=f"✓  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns · {os.path.basename(path)}",
                fg=GREEN)
            self.log(f"✓  CSV loaded: {len(self.csv_rows)} rows from {os.path.basename(path)}", 'ok')
            self.update_combos()
        except Exception as e:
            messagebox.showerror('Error reading CSV', str(e))

    def update_combos(self):
        options = ['(skip)'] + self.csv_headers
        hints = {
            'Filename *': ['filename','file','name','image'],
            'Title': ['title'],
            'Keywords': ['keyword','tag','kw'],
            'Description': ['desc','caption','description'],
            'Copyright': ['copy','copyright','rights'],
        }
        vars_map = {
            'Filename *': self.col_file, 'Title': self.col_title,
            'Keywords': self.col_kw, 'Description': self.col_desc,
            'Copyright': self.col_copy,
        }
        for label, cb in self.col_combos.items():
            cb['values'] = options
            guessed = next((c for h in hints.get(label,[])
                           for c in self.csv_headers if h in c.lower()), '')
            vars_map[label].set(guessed or '(skip)')

    def browse_folder(self):
        path = filedialog.askdirectory(title='Select image folder')
        if path: self.folder_path.set(path)

    def start_embed(self):
        if self.running: return
        et = find_exiftool()
        if not et:
            messagebox.showerror('ExifTool not found',
                'Place exiftool.exe in the same folder as this app.\nDownload: https://exiftool.org')
            return
        if not self.csv_rows:
            messagebox.showerror('No CSV', 'Load a CSV file first.'); return
        if not self.folder_path.get():
            messagebox.showerror('No folder', 'Select the image folder.'); return
        fc = self.col_file.get()
        if not fc or fc == '(skip)':
            messagebox.showerror('No filename column', 'Select the filename column in Step 2.'); return
        self.running = True
        self.embed_btn.config(state='disabled', text='Processing…')
        threading.Thread(target=self.run_embed, args=(et,), daemon=True).start()

    def run_embed(self, et):
        folder = self.folder_path.get()
        col_f  = self.col_file.get()
        col_t  = self.col_title.get()
        col_k  = self.col_kw.get()
        col_d  = self.col_desc.get()
        col_c  = self.col_copy.get()
        total  = len(self.csv_rows)
        ok = skipped = errors = 0
        self.root.after(0, lambda: self.progress.configure(maximum=total, value=0))

        for i, row in enumerate(self.csv_rows):
            filename = (row.get(col_f) or '').strip()
            if not filename:
                skipped += 1
                self.root.after(0, lambda n=i+1,t=total: self._prog(n,t)); continue
            filepath = os.path.join(folder, filename)
            if not os.path.exists(filepath):
                self.root.after(0, lambda fn=filename: self.log(f'⚠  Not found: {fn}','warn'))
                skipped += 1
                self.root.after(0, lambda n=i+1,t=total: self._prog(n,t)); continue

            cmd = [et, '-overwrite_original', '-codedcharacterset=UTF8']
            title = (row.get(col_t) or '').strip() if col_t and col_t!='(skip)' else ''
            kw_raw= (row.get(col_k) or '').strip() if col_k and col_k!='(skip)' else ''
            desc  = (row.get(col_d) or '').strip() if col_d and col_d!='(skip)' else ''
            copy  = (row.get(col_c) or '').strip() if col_c and col_c!='(skip)' else ''

            if title: cmd += [f'-Title={title}', f'-ObjectName={title}', f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd += [f'-Keywords={kw}', f'-Subject={kw}']
            if desc:  cmd += [f'-Description={desc}', f'-Caption-Abstract={desc}']
            if copy:  cmd += [f'-Copyright={copy}', f'-CopyrightNotice={copy}', f'-Rights={copy}']
            cmd.append(filepath)

            try:
                flags = subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        timeout=30, creationflags=flags)
                if result.returncode == 0:
                    ok += 1
                    self.root.after(0, lambda fn=filename: self.log(f'✓  {fn}','ok'))
                else:
                    errors += 1
                    err = (result.stderr or result.stdout or 'Unknown error').strip()
                    self.root.after(0, lambda fn=filename,e=err: self.log(f'✗  {fn}  —  {e}','err'))
            except Exception as e:
                errors += 1
                self.root.after(0, lambda fn=filename,e=str(e): self.log(f'✗  {fn}  —  {e}','err'))
            self.root.after(0, lambda n=i+1,t=total: self._prog(n,t))

        summary = f'\n  Done!   ✓ {ok} embedded     ⚠ {skipped} skipped     ✗ {errors} errors\n'
        self.root.after(0, lambda: (
            self.log(summary,'info'),
            self.embed_btn.config(state='normal', text='▶   Embed Metadata Now'),
            setattr(self,'running',False)
        ))

    def _prog(self, n, total):
        self.progress.configure(value=n)
        self.prog_label.configure(text=f'{n} of {total} files processed')

if __name__ == '__main__':
    root = tk.Tk()
    try: root.iconbitmap(default='')
    except: pass
    app = MetadataApp(root)
    root.mainloop()
