import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, subprocess, os, sys, threading, datetime

def find_exiftool():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
        bundled = os.path.join(base, 'exiftool_pkg', 'exiftool.exe')
        if os.path.exists(bundled): return bundled
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

def find_file_any_ext(folder, csv_filename):
    """Match file by base name ignoring extension."""
    base = os.path.splitext(csv_filename)[0]
    # First try exact match
    exact = os.path.join(folder, csv_filename)
    if os.path.exists(exact): return exact
    # Try matching base name with any extension
    try:
        for f in os.listdir(folder):
            if os.path.splitext(f)[0].lower() == base.lower():
                return os.path.join(folder, f)
    except Exception:
        pass
    return None

# ── Dark theme ─────────────────────────────────────────────────────────
BG   = '#141412'; BG2  = '#1e1e1c'; BG3  = '#242422'; BG4 = '#0e0e0c'
TEXT = '#e8e8e4'; TEXT2= '#9a9a96'; TEXT3= '#4a4a48'
BLUE = '#3b8fe8'; BLUE2= '#2a7fd4'
GREEN= '#4caf72'; GREEN2='#1a3020'; GREEN3='#2a4830'
RED  = '#e87070'; RED2 = '#2a1a1a'; RED3 = '#4a2828'
AMB  = '#f0c060'; AMB2 = '#2a2010'; AMB3 = '#4a3818'
BDR  = '#2e2e2c'; BDR2 = '#3a3a38'

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Metadata Embedder")
        self.root.geometry("700x500")
        self.root.minsize(500, 420)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # Try to set icon
        icon_path = self._find_icon()
        if icon_path:
            try: self.root.iconbitmap(icon_path)
            except: pass

        self.csv_path    = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.col_file    = tk.StringVar()
        self.col_title   = tk.StringVar()
        self.col_kw      = tk.StringVar()
        self.col_desc    = tk.StringVar()
        self.col_copy    = tk.StringVar()
        self.csv_headers = []
        self.csv_rows    = []
        self.running     = False
        self.log_visible = True

        self.build_ui()
        self.check_exiftool()

    def _find_icon(self):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        for name in ['icon.ico', 'app.ico']:
            p = os.path.join(base, name)
            if os.path.exists(p): return p
        return None

    def ts(self):
        return datetime.datetime.now().strftime('%H:%M:%S')

    def build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=BG3, background=BG3,
            foreground=TEXT, selectbackground=BLUE, selectforeground=TEXT,
            arrowcolor=TEXT2, bordercolor=BDR)
        style.map('TCombobox', fieldbackground=[('readonly',BG3)],
            foreground=[('readonly',TEXT)], bordercolor=[('focus',BLUE)])
        style.configure('Vertical.TScrollbar', background=BG3,
            troughcolor=BG2, arrowcolor=TEXT3, bordercolor=BDR)
        style.configure('TProgressbar', background=BLUE, troughcolor=BG3,
            bordercolor=BDR, lightcolor=BLUE, darkcolor=BLUE2)

        # Title bar
        tbar = tk.Frame(self.root, bg=BG4, padx=14, pady=9)
        tbar.pack(fill='x')
        tk.Label(tbar, text="M", font=('Segoe UI',11,'bold'),
            bg=BLUE, fg='white', width=2, padx=4).pack(side='left')
        tk.Label(tbar, text="  Stock Metadata Embedder",
            font=('Segoe UI',12,'bold'), bg=BG4, fg=TEXT).pack(side='left')
        tk.Label(tbar, text="v1.7", font=('Segoe UI',9),
            bg=BG4, fg=TEXT3).pack(side='left', padx=6)

        # Main area
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(fill='both', expand=True)

        # Left panel
        self.left = tk.Frame(self.main, bg=BG, width=290)
        self.left.pack(side='left', fill='y', padx=(10,5), pady=10)
        self.left.pack_propagate(False)

        self.build_step1()
        self.build_step2()
        self.build_step3()
        self.build_action_row()

        # Right panel (log)
        self.right = tk.Frame(self.main, bg=BG2,
            highlightbackground=BDR, highlightthickness=1)
        self.right.pack(side='left', fill='both', expand=True,
            padx=(0,10), pady=10)
        self.build_log()

        # Status bar
        self.build_statusbar()

    def card(self, parent, title, num):
        outer = tk.Frame(parent, bg=BG, pady=4)
        outer.pack(fill='x')
        inner = tk.Frame(outer, bg=BG2,
            highlightbackground=BDR, highlightthickness=1)
        inner.pack(fill='x')
        hdr = tk.Frame(inner, bg=BG3, padx=10, pady=7)
        hdr.pack(fill='x')
        tk.Label(hdr, text=f" {num} ", font=('Segoe UI',9,'bold'),
            bg=BLUE, fg='white').pack(side='left')
        tk.Label(hdr, text=f"  {title}", font=('Segoe UI',9,'bold'),
            bg=BG3, fg=TEXT2).pack(side='left')
        tk.Frame(inner, bg=BDR, height=1).pack(fill='x')
        body = tk.Frame(inner, bg=BG2, padx=10, pady=8)
        body.pack(fill='x')
        return body

    def mini_label(self, parent, text):
        tk.Label(parent, text=text, font=('Segoe UI',8,'bold'),
            bg=BG2, fg=TEXT3,
            anchor='w').pack(fill='x', pady=(4,1))

    def field_entry(self, parent, var, readonly=False):
        state = 'readonly' if readonly else 'normal'
        e = tk.Entry(parent, textvariable=var, font=('Segoe UI',9),
            bg=BG3, fg=TEXT, relief='flat', insertbackground=TEXT,
            readonlybackground=BG3, state=state,
            highlightbackground=BDR, highlightthickness=1)
        e.pack(fill='x', pady=(0,4))
        return e

    def browse_btn(self, parent, text, cmd):
        tk.Button(parent, text=text, command=cmd,
            font=('Segoe UI',9,'bold'), bg=BG3, fg=BLUE,
            relief='flat', padx=8, pady=4, cursor='hand2',
            activebackground=BDR2, activeforeground=BLUE,
            highlightbackground=BDR, highlightthickness=1).pack(fill='x')

    def build_step1(self):
        body = self.card(self.left, 'Load CSV', '1')
        self.mini_label(body, 'CSV FILE')
        self.field_entry(body, self.csv_path, readonly=True)
        self.browse_btn(body, '  Browse CSV…', self.load_csv)
        self.csv_info = tk.Label(body, text='', font=('Segoe UI',8),
            bg=BG2, fg=GREEN, anchor='w')
        self.csv_info.pack(fill='x', pady=(3,0))

    def build_step2(self):
        body = self.card(self.left, 'Map columns', '2')
        self.col_combos = {}
        fields = [
            ('FILENAME *', self.col_file, True),
            ('TITLE', self.col_title, False),
            ('KEYWORDS', self.col_kw, False),
            ('DESCRIPTION', self.col_desc, False),
            ('COPYRIGHT', self.col_copy, False),
        ]
        grid = tk.Frame(body, bg=BG2)
        grid.pack(fill='x')
        for i,(label,var,req) in enumerate(fields):
            col = i%2; row_n = i//2
            cell = tk.Frame(grid, bg=BG2, padx=2, pady=2)
            cell.grid(row=row_n, column=col, sticky='ew', padx=2)
            grid.columnconfigure(col, weight=1)
            lbl = label + (' ●' if req else '')
            tk.Label(cell, text=lbl, font=('Segoe UI',8,'bold'),
                bg=BG2, fg=TEXT3 if not req else TEXT2,
                anchor='w').pack(fill='x')
            cb = ttk.Combobox(cell, textvariable=var,
                state='readonly', font=('Segoe UI',9))
            cb.pack(fill='x', pady=(1,0))
            self.col_combos[label] = cb

    def build_step3(self):
        body = self.card(self.left, 'Image folder', '3')
        self.mini_label(body, 'FOLDER PATH')
        self.field_entry(body, self.folder_path, readonly=True)
        self.browse_btn(body, '  Browse folder…', self.browse_folder)
        self.folder_info = tk.Label(body, text='', font=('Segoe UI',8),
            bg=BG2, fg=GREEN, anchor='w')
        self.folder_info.pack(fill='x', pady=(3,0))

    def build_action_row(self):
        row = tk.Frame(self.left, bg=BG, pady=6)
        row.pack(fill='x')
        # Reset — small, left
        self.reset_btn = tk.Button(row, text='↺ Reset',
            command=self.reset_all,
            font=('Segoe UI',9,'bold'), bg=RED2, fg=RED,
            relief='flat', padx=10, pady=9, cursor='hand2',
            activebackground=RED3, activeforeground='#ffaaaa',
            highlightbackground=RED3, highlightthickness=1)
        self.reset_btn.pack(side='left', padx=(0,6))
        # Embed — big, fills rest
        self.embed_btn = tk.Button(row, text='▶  Embed Metadata Now',
            command=self.start_embed,
            font=('Segoe UI',11,'bold'), bg=BLUE, fg='white',
            relief='flat', padx=0, pady=9, cursor='hand2',
            activebackground=BLUE2, activeforeground='white')
        self.embed_btn.pack(side='left', fill='x', expand=True)

    def build_log(self):
        hdr = tk.Frame(self.right, bg=BG3,
            highlightbackground=BDR, highlightthickness=0)
        hdr.pack(fill='x')
        tk.Frame(hdr, bg=BDR, height=1).pack(fill='x', side='bottom')
        inner_hdr = tk.Frame(hdr, bg=BG3, padx=10, pady=7)
        inner_hdr.pack(fill='x')
        tk.Label(inner_hdr, text='Activity Log',
            font=('Segoe UI',9,'bold'), bg=BG3, fg=TEXT3).pack(side='left')
        self.log_toggle = tk.Button(inner_hdr, text='◀',
            command=self.toggle_log,
            font=('Segoe UI',9), bg=BG4, fg=TEXT3,
            relief='flat', padx=6, pady=2, cursor='hand2',
            activebackground=BG3, activeforeground=TEXT2)
        self.log_toggle.pack(side='right')

        self.log_frame = tk.Frame(self.right, bg=BG2)
        self.log_frame.pack(fill='both', expand=True)

        self.log_text = tk.Text(self.log_frame, font=('Consolas',9),
            bg=BG2, fg=TEXT, relief='flat', state='disabled',
            wrap='word', insertbackground=TEXT,
            selectbackground=BLUE, padx=8, pady=6)
        sb = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.log_text.pack(fill='both', expand=True)

        self.log_text.tag_config('ok',   foreground=GREEN)
        self.log_text.tag_config('warn', foreground=AMB)
        self.log_text.tag_config('err',  foreground=RED)
        self.log_text.tag_config('info', foreground=BLUE)
        self.log_text.tag_config('ts',   foreground=TEXT3)
        self.log_text.tag_config('dim',  foreground=TEXT3)

        clr = tk.Button(self.right, text='Clear log',
            command=self.clear_log,
            font=('Segoe UI',8), bg=BG3, fg=TEXT3,
            relief='flat', cursor='hand2', pady=3,
            activebackground=BG4, activeforeground=TEXT2)
        clr.pack(fill='x')

    def toggle_log(self):
        if self.log_visible:
            self.right.pack_forget()
            self.log_visible = False
            self.root.geometry('300x500')
        else:
            self.right.pack(side='left', fill='both', expand=True,
                padx=(0,10), pady=10)
            self.log_visible = True
            self.root.geometry('700x500')
            self.log_toggle.configure(text='◀')

    def build_statusbar(self):
        self.sbar = tk.Frame(self.root, bg=BG4,
            highlightbackground=BDR, highlightthickness=1)
        self.sbar.pack(fill='x', side='bottom')
        inner = tk.Frame(self.sbar, bg=BG4, padx=10, pady=5)
        inner.pack(fill='x')

        self.sb_status = tk.Label(inner, text='Ready',
            font=('Segoe UI',9), bg=BG4, fg=TEXT3, anchor='w')
        self.sb_status.pack(side='left')

        self.sb_right = tk.Label(inner, text='ExifTool · not checked',
            font=('Segoe UI',8), bg=BG4, fg=TEXT3, anchor='e')
        self.sb_right.pack(side='right')

        self.sb_progress = ttk.Progressbar(inner, mode='determinate',
            length=120, style='TProgressbar')
        self.sb_progress.pack(side='right', padx=(0,10))

        # Stat pills
        self.pill_frame = tk.Frame(inner, bg=BG4)
        self.pill_frame.pack(side='left', padx=(12,0))
        self.pill_ok   = self._pill(self.pill_frame, '0 embedded', GREEN2, GREEN, GREEN3)
        self.pill_warn = self._pill(self.pill_frame, '0 not found', AMB2, AMB, AMB3)
        self.pill_err  = self._pill(self.pill_frame, '0 errors', RED2, RED, RED3)

    def _pill(self, parent, text, bg, fg, border):
        lbl = tk.Label(parent, text=text, font=('Segoe UI',8,'bold'),
            bg=bg, fg=fg, padx=8, pady=2,
            highlightbackground=border, highlightthickness=1)
        lbl.pack(side='left', padx=3)
        return lbl

    def set_status(self, msg, color=None):
        self.sb_status.configure(text=msg,
            fg=color if color else TEXT3)

    def log(self, msg, tag=''):
        self.log_text.configure(state='normal')
        ts = self.ts()
        self.log_text.insert('end', f'{ts}  ', 'ts')
        self.log_text.insert('end', msg+'\n', tag)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0','end')
        self.log_text.configure(state='disabled')

    def check_exiftool(self):
        et = find_exiftool()
        if et:
            self.log('✓  ExifTool ready', 'ok')
            self.sb_right.configure(text='ExifTool · ready', fg=GREEN)
        else:
            self.log('⚠  ExifTool not found — place exiftool.exe next to this app', 'warn')
            self.sb_right.configure(text='ExifTool · missing', fg=RED)

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
            info = f'✓  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns'
            self.csv_info.configure(text=info, fg=GREEN)
            self.log(f'✓  CSV loaded — {len(self.csv_rows)} rows · {os.path.basename(path)}', 'ok')
            self.set_status(f'CSV loaded: {len(self.csv_rows)} rows', GREEN)
            self.update_combos()
        except Exception as e:
            messagebox.showerror('Error reading CSV', str(e))

    def update_combos(self):
        options = ['(skip)'] + self.csv_headers
        hints = {
            'FILENAME *': ['filename','file','name','image'],
            'TITLE': ['title'],
            'KEYWORDS': ['keyword','tag','kw'],
            'DESCRIPTION': ['desc','caption','description'],
            'COPYRIGHT': ['copy','copyright','rights'],
        }
        vars_map = {
            'FILENAME *': self.col_file, 'TITLE': self.col_title,
            'KEYWORDS': self.col_kw, 'DESCRIPTION': self.col_desc,
            'COPYRIGHT': self.col_copy,
        }
        for label, cb in self.col_combos.items():
            cb['values'] = options
            guessed = next((c for h in hints.get(label,[])
                for c in self.csv_headers if h in c.lower()), '')
            vars_map[label].set(guessed or '(skip)')

    def browse_folder(self):
        path = filedialog.askdirectory(title='Select image folder')
        if not path: return
        self.folder_path.set(path)
        try:
            count = len([f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path,f))])
            self.folder_info.configure(text=f'✓  {count} files in folder', fg=GREEN)
            self.log(f'✓  Folder set — {count} files · {path}', 'ok')
            self.set_status(f'Folder loaded: {count} files', GREEN)
        except Exception:
            self.folder_info.configure(text='✓  Folder set', fg=GREEN)

    def reset_all(self):
        if self.running:
            messagebox.showwarning('Busy','Wait for current job to finish.'); return
        if not messagebox.askyesno('Reset','Clear everything and start fresh?'): return
        self.csv_path.set(''); self.folder_path.set('')
        self.col_file.set(''); self.col_title.set('')
        self.col_kw.set(''); self.col_desc.set(''); self.col_copy.set('')
        self.csv_headers=[]; self.csv_rows=[]
        self.csv_info.configure(text='')
        self.folder_info.configure(text='')
        for cb in self.col_combos.values(): cb['values']=[]
        self.sb_progress.configure(value=0)
        self.pill_ok.configure(text='0 embedded')
        self.pill_warn.configure(text='0 not found')
        self.pill_err.configure(text='0 errors')
        self.embed_btn.configure(state='normal', text='▶  Embed Metadata Now')
        self.clear_log()
        self.log('↺  Reset — ready for new batch', 'info')
        self.set_status('Reset complete', BLUE)

    def start_embed(self):
        if self.running: return
        et = find_exiftool()
        if not et:
            messagebox.showerror('ExifTool not found',
                'Place exiftool.exe in the same folder as this app.\nDownload: https://exiftool.org')
            return
        if not self.csv_rows:
            messagebox.showerror('No CSV','Load a CSV file first.'); return
        if not self.folder_path.get():
            messagebox.showerror('No folder','Select the image folder.'); return
        fc = self.col_file.get()
        if not fc or fc=='(skip)':
            messagebox.showerror('No filename column','Select the filename column in Step 2.'); return
        self.running=True
        self.embed_btn.configure(state='disabled', text='Processing…')
        threading.Thread(target=self.run_embed, args=(et,), daemon=True).start()

    def run_embed(self, et):
        folder  = self.folder_path.get()
        col_f   = self.col_file.get()
        col_t   = self.col_title.get()
        col_k   = self.col_kw.get()
        col_d   = self.col_desc.get()
        col_c   = self.col_copy.get()
        total   = len(self.csv_rows)
        ok=skipped=errors=0

        self.root.after(0, lambda: self.sb_progress.configure(maximum=total,value=0))
        self.root.after(0, lambda: self.log(f'▶  Batch started — {total} rows','info'))
        self.root.after(0, lambda: self.set_status(f'Processing 0 of {total}…', BLUE))

        for i, row in enumerate(self.csv_rows):
            filename = (row.get(col_f) or '').strip()
            if not filename:
                skipped+=1
                self.root.after(0, lambda n=i+1,t=total: self._prog(n,t,ok,skipped,errors))
                continue

            filepath = find_file_any_ext(folder, filename)
            if not filepath:
                self.root.after(0, lambda fn=filename:
                    self.log(f'⚠  Not found: {fn} (tried any extension)','warn'))
                skipped+=1
                self.root.after(0, lambda n=i+1,t=total: self._prog(n,t,ok,skipped,errors))
                continue

            cmd=[et,'-overwrite_original','-codedcharacterset=UTF8']
            title =(row.get(col_t) or '').strip() if col_t and col_t!='(skip)' else ''
            kw_raw=(row.get(col_k) or '').strip() if col_k and col_k!='(skip)' else ''
            desc  =(row.get(col_d) or '').strip() if col_d and col_d!='(skip)' else ''
            copy  =(row.get(col_c) or '').strip() if col_c and col_c!='(skip)' else ''

            if title: cmd+=[f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd+=[f'-Keywords={kw}',f'-Subject={kw}']
            if desc:  cmd+=[f'-Description={desc}',f'-Caption-Abstract={desc}']
            if copy:  cmd+=[f'-Copyright={copy}',f'-CopyrightNotice={copy}',f'-Rights={copy}']
            cmd.append(filepath)

            try:
                flags = subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                result=subprocess.run(cmd,capture_output=True,text=True,
                    timeout=30,creationflags=flags)
                actual_name = os.path.basename(filepath)
                if result.returncode==0:
                    ok+=1
                    self.root.after(0,lambda fn=actual_name: self.log(f'✓  {fn}','ok'))
                else:
                    errors+=1
                    err=(result.stderr or result.stdout or 'Unknown').strip()
                    self.root.after(0,lambda fn=actual_name,e=err:
                        self.log(f'✗  {fn}  —  {e}','err'))
            except Exception as e:
                errors+=1
                self.root.after(0,lambda fn=filename,e=str(e):
                    self.log(f'✗  {fn}  —  {e}','err'))

            self.root.after(0, lambda n=i+1,t=total,o=ok,s=skipped,er=errors:
                self._prog(n,t,o,s,er))

        summary=(f'● Batch complete — '
                 f'{ok} embedded · {skipped} not found · {errors} errors')
        self.root.after(0, lambda: (
            self.log(summary,'info'),
            self.set_status(summary, BLUE),
            self.embed_btn.configure(state='normal', text='▶  Embed Metadata Now'),
            setattr(self,'running',False)
        ))

    def _prog(self, n, total, ok, skipped, errors):
        self.sb_progress.configure(value=n)
        self.set_status(f'Processing {n} of {total}…', BLUE)
        self.pill_ok.configure(text=f'{ok} embedded')
        self.pill_warn.configure(text=f'{skipped} not found')
        self.pill_err.configure(text=f'{errors} errors')

if __name__=='__main__':
    root=tk.Tk()
    app=MetadataApp(root)
    root.mainloop()
