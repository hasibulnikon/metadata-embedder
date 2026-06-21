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
    base = os.path.splitext(csv_filename)[0]
    exact = os.path.join(folder, csv_filename)
    if os.path.exists(exact): return exact
    try:
        for f in os.listdir(folder):
            if os.path.splitext(f)[0].lower() == base.lower():
                return os.path.join(folder, f)
    except Exception:
        pass
    return None

BG   = '#141412'; BG2  = '#1e1e1c'; BG3  = '#242422'; BG4 = '#0e0e0c'
TEXT = '#e8e8e4'; TEXT2= '#9a9a96'; TEXT3= '#4a4a48'
BLUE = '#3b8fe8'; BLUE2= '#2a7fd4'
GREEN= '#4caf72'; GREEN2='#1a3020'; GREEN3='#2a4830'
RED  = '#e87070'; RED2 = '#2a1a1a'; RED3 = '#4a2828'
AMB  = '#f0c060'; AMB2 = '#2a2010'; AMB3 = '#4a3818'
BDR  = '#2e2e2c'; BDR2 = '#3a3a38'

WIN_W_FULL = 720
WIN_W_SLIM = 320
WIN_H      = 560

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Metadata Embedder")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.log_visible = True
        self.running = False

        self.csv_path    = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.col_file    = tk.StringVar()
        self.col_title   = tk.StringVar()
        self.col_kw      = tk.StringVar()
        self.col_desc    = tk.StringVar()
        self.col_copy    = tk.StringVar()
        self.csv_headers = []
        self.csv_rows    = []

        icon_path = self._find_icon()
        if icon_path:
            try: self.root.iconbitmap(icon_path)
            except: pass

        self.build_ui()
        self._set_window(WIN_W_FULL, WIN_H, center=True)
        self.check_exiftool()

    def _find_icon(self):
        base = sys._MEIPASS if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
        for n in ['icon.ico','app.ico']:
            p = os.path.join(base, n)
            if os.path.exists(p): return p
        return None

    def _set_window(self, w, h, center=False):
        if center:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x  = (sw - w) // 2
            y  = (sh - h) // 2
            self.root.geometry(f'{w}x{h}+{x}+{y}')
        else:
            # Keep current position, just resize
            self.root.geometry(f'{w}x{h}')

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

        # ── Title bar ──────────────────────────────────────────────────
        tbar = tk.Frame(self.root, bg=BG4, padx=14, pady=9)
        tbar.pack(fill='x')
        tk.Label(tbar, text=" M ", font=('Segoe UI',11,'bold'),
            bg=BLUE, fg='white').pack(side='left')
        tk.Label(tbar, text="  Stock Metadata Embedder",
            font=('Segoe UI',12,'bold'), bg=BG4, fg=TEXT).pack(side='left')
        tk.Label(tbar, text="v1.8", font=('Segoe UI',9),
            bg=BG4, fg=TEXT3).pack(side='left', padx=6)
        tk.Label(tbar, text="© HASIBNIKON", font=('Segoe UI',8),
            bg=BG4, fg=TEXT3).pack(side='right', padx=6)

        # ── Body: left panel + right log ───────────────────────────────
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill='both', expand=True)

        # Left panel — fixed width, scrollable
        left_outer = tk.Frame(self.body, bg=BG, width=300)
        left_outer.pack(side='left', fill='y')
        left_outer.pack_propagate(False)

        canvas = tk.Canvas(left_outer, bg=BG, highlightthickness=0, width=300)
        vsb = ttk.Scrollbar(left_outer, orient='vertical', command=canvas.yview)
        self.left = tk.Frame(canvas, bg=BG, padx=10, pady=6)
        self.left.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=self.left, anchor='nw', width=280)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(
            int(-1*(e.delta/120)),'units'))

        self.build_step1()
        self.build_step2()
        self.build_step3()
        self.build_action_row()

        # Right panel — log
        self.right_outer = tk.Frame(self.body, bg=BG)
        self.right_outer.pack(side='left', fill='both', expand=True, padx=(0,0))
        self.build_log()

        # ── Status bar ─────────────────────────────────────────────────
        self.build_statusbar()

    def card(self, title, num):
        outer = tk.Frame(self.left, bg=BG, pady=4)
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
            bg=BG2, fg=TEXT3, anchor='w').pack(fill='x', pady=(4,1))

    def field_entry(self, parent, var):
        e = tk.Entry(parent, textvariable=var, font=('Segoe UI',9),
            bg=BG3, fg=TEXT, relief='flat', insertbackground=TEXT,
            readonlybackground=BG3, state='readonly',
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
        body = self.card('Load CSV', '1')
        self.mini_label(body, 'CSV FILE')
        self.field_entry(body, self.csv_path)
        self.browse_btn(body, '  Browse CSV…', self.load_csv)
        self.csv_info = tk.Label(body, text='', font=('Segoe UI',8),
            bg=BG2, fg=GREEN, anchor='w')
        self.csv_info.pack(fill='x', pady=(3,0))

    def build_step2(self):
        body = self.card('Map columns', '2')
        self.col_combos = {}
        fields = [
            ('FILENAME *', self.col_file),
            ('TITLE',      self.col_title),
            ('KEYWORDS',   self.col_kw),
            ('DESCRIPTION',self.col_desc),
            ('COPYRIGHT',  self.col_copy),
        ]
        grid = tk.Frame(body, bg=BG2)
        grid.pack(fill='x')
        for i,(label,var) in enumerate(fields):
            col = i%2; row_n = i//2
            cell = tk.Frame(grid, bg=BG2, padx=2, pady=2)
            cell.grid(row=row_n, column=col, sticky='ew', padx=2)
            grid.columnconfigure(col, weight=1)
            tk.Label(cell, text=label, font=('Segoe UI',8,'bold'),
                bg=BG2, fg=TEXT3, anchor='w').pack(fill='x')
            cb = ttk.Combobox(cell, textvariable=var,
                state='readonly', font=('Segoe UI',9))
            cb.pack(fill='x', pady=(1,0))
            self.col_combos[label] = cb

    def build_step3(self):
        body = self.card('Image folder', '3')
        self.mini_label(body, 'FOLDER PATH')
        self.field_entry(body, self.folder_path)
        self.browse_btn(body, '  Browse folder…', self.browse_folder)
        self.folder_info = tk.Label(body, text='', font=('Segoe UI',8),
            bg=BG2, fg=GREEN, anchor='w')
        self.folder_info.pack(fill='x', pady=(3,0))

    def build_action_row(self):
        row = tk.Frame(self.left, bg=BG, pady=6)
        row.pack(fill='x')
        self.reset_btn = tk.Button(row, text='↺ Reset',
            command=self.reset_all,
            font=('Segoe UI',9,'bold'), bg=RED2, fg=RED,
            relief='flat', padx=10, pady=9, cursor='hand2',
            activebackground=RED3, activeforeground='#ffaaaa',
            highlightbackground=RED3, highlightthickness=1)
        self.reset_btn.pack(side='left', padx=(0,6))
        self.embed_btn = tk.Button(row, text='▶  Embed Metadata Now',
            command=self.start_embed,
            font=('Segoe UI',11,'bold'), bg=BLUE, fg='white',
            relief='flat', padx=0, pady=9, cursor='hand2',
            activebackground=BLUE2, activeforeground='white')
        self.embed_btn.pack(side='left', fill='x', expand=True)

    def build_log(self):
        # Log header with toggle button
        hdr = tk.Frame(self.right_outer, bg=BG3,
            highlightbackground=BDR, highlightthickness=0)
        hdr.pack(fill='x')
        tk.Frame(hdr, bg=BDR, height=1).pack(fill='x', side='bottom')
        inner_hdr = tk.Frame(hdr, bg=BG3, padx=10, pady=7)
        inner_hdr.pack(fill='x')

        self.log_toggle = tk.Button(inner_hdr,
            text='◀ Hide log',
            command=self.toggle_log,
            font=('Segoe UI',8,'bold'), bg=BG4, fg=TEXT3,
            relief='flat', padx=8, pady=2, cursor='hand2',
            activebackground=BG3, activeforeground=TEXT2)
        self.log_toggle.pack(side='right')
        tk.Label(inner_hdr, text='Activity Log',
            font=('Segoe UI',9,'bold'), bg=BG3, fg=TEXT3).pack(side='left')

        # Log body
        self.log_frame = tk.Frame(self.right_outer, bg=BG2)
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

        tk.Button(self.right_outer, text='Clear log',
            command=self.clear_log,
            font=('Segoe UI',8), bg=BG3, fg=TEXT3,
            relief='flat', cursor='hand2', pady=3,
            activebackground=BG4, activeforeground=TEXT2).pack(fill='x')

    def toggle_log(self):
        if self.log_visible:
            # Hide log panel
            self.right_outer.pack_forget()
            self.log_visible = False
            # Add show button to left panel bottom
            self.show_log_btn = tk.Button(self.left, text='▶ Show log',
                command=self.toggle_log,
                font=('Segoe UI',8,'bold'), bg=BG3, fg=TEXT3,
                relief='flat', padx=8, pady=4, cursor='hand2',
                activebackground=BDR2, activeforeground=TEXT2)
            self.show_log_btn.pack(fill='x', pady=(4,0))
            self._set_window(WIN_W_SLIM, WIN_H)
        else:
            # Remove show button
            if hasattr(self, 'show_log_btn'):
                self.show_log_btn.destroy()
            # Show log panel
            self.right_outer.pack(side='left', fill='both', expand=True)
            self.log_visible = True
            self.log_toggle.configure(text='◀ Hide log')
            self._set_window(WIN_W_FULL, WIN_H)

    def build_statusbar(self):
        self.sbar = tk.Frame(self.root, bg=BG4,
            highlightbackground=BDR, highlightthickness=1)
        self.sbar.pack(fill='x', side='bottom')
        inner = tk.Frame(self.sbar, bg=BG4, padx=10, pady=5)
        inner.pack(fill='x')

        self.sb_status = tk.Label(inner, text='Ready',
            font=('Segoe UI',9), bg=BG4, fg=TEXT3, anchor='w')
        self.sb_status.pack(side='left')

        self.sb_right = tk.Label(inner, text='ExifTool · checking…',
            font=('Segoe UI',8), bg=BG4, fg=TEXT3, anchor='e')
        self.sb_right.pack(side='right')

        self.sb_progress = ttk.Progressbar(inner, mode='determinate',
            length=100, style='TProgressbar')
        self.sb_progress.pack(side='right', padx=(0,10))

        self.pill_frame = tk.Frame(inner, bg=BG4)
        self.pill_frame.pack(side='left', padx=(12,0))
        self.pill_ok   = self._pill('0 embedded', GREEN2, GREEN, GREEN3)
        self.pill_warn = self._pill('0 not found', AMB2, AMB, AMB3)
        self.pill_err  = self._pill('0 errors', RED2, RED, RED3)

    def _pill(self, text, bg, fg, border):
        lbl = tk.Label(self.pill_frame, text=text,
            font=('Segoe UI',8,'bold'),
            bg=bg, fg=fg, padx=8, pady=2,
            highlightbackground=border, highlightthickness=1)
        lbl.pack(side='left', padx=3)
        return lbl

    def set_status(self, msg, color=None):
        self.sb_status.configure(text=msg, fg=color if color else TEXT3)

    def log(self, msg, tag=''):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', f'{self.ts()}  ', 'ts')
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
            self.log('⚠  ExifTool not found — place exiftool.exe next to this app','warn')
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
            self.log(f'✓  CSV loaded — {len(self.csv_rows)} rows · {os.path.basename(path)}','ok')
            self.set_status(f'CSV loaded: {len(self.csv_rows)} rows', GREEN)
            self.update_combos()
        except Exception as e:
            messagebox.showerror('Error reading CSV', str(e))

    def update_combos(self):
        options = ['(skip)'] + self.csv_headers
        hints = {
            'FILENAME *': ['filename','file','name','image'],
            'TITLE':      ['title'],
            'KEYWORDS':   ['keyword','tag','kw'],
            'DESCRIPTION':['desc','caption','description'],
            'COPYRIGHT':  ['copy','copyright','rights'],
        }
        vars_map = {
            'FILENAME *': self.col_file,  'TITLE': self.col_title,
            'KEYWORDS':   self.col_kw,    'DESCRIPTION': self.col_desc,
            'COPYRIGHT':  self.col_copy,
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
            self.log(f'✓  Folder set — {count} files','ok')
            self.set_status(f'Folder loaded: {count} files', GREEN)
        except Exception:
            self.folder_info.configure(text='✓  Folder set', fg=GREEN)

    def reset_all(self):
        if self.running:
            messagebox.showwarning('Busy','Wait for current job to finish.'); return
        if not messagebox.askyesno('Reset','Clear everything and start fresh?'): return
        for v in [self.csv_path, self.folder_path, self.col_file,
                  self.col_title, self.col_kw, self.col_desc, self.col_copy]:
            v.set('')
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
        self.log('↺  Reset — ready for new batch','info')
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
            messagebox.showerror('No filename column',
                'Select the filename column in Step 2.'); return
        self.running=True
        self.embed_btn.configure(state='disabled', text='Processing…')
        threading.Thread(target=self.run_embed, args=(et,), daemon=True).start()

    def run_embed(self, et):
        folder = self.folder_path.get()
        col_f  = self.col_file.get()
        col_t  = self.col_title.get()
        col_k  = self.col_kw.get()
        col_d  = self.col_desc.get()
        col_c  = self.col_copy.get()
        total  = len(self.csv_rows)
        ok=skipped=errors=0

        self.root.after(0, lambda: self.sb_progress.configure(maximum=total,value=0))
        self.root.after(0, lambda: self.log(f'▶  Batch started — {total} rows','info'))
        self.root.after(0, lambda: self.set_status(f'Processing 0 of {total}…',BLUE))

        for i, row in enumerate(self.csv_rows):
            filename = (row.get(col_f) or '').strip()
            if not filename:
                skipped+=1
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue

            filepath = find_file_any_ext(folder, filename)
            if not filepath:
                self.root.after(0,lambda fn=filename:
                    self.log(f'⚠  Not found: {fn}','warn'))
                skipped+=1
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue

            cmd=[et,'-overwrite_original','-codedcharacterset=UTF8']
            title =(row.get(col_t) or '').strip() if col_t and col_t!='(skip)' else ''
            kw_raw=(row.get(col_k) or '').strip() if col_k and col_k!='(skip)' else ''
            desc  =(row.get(col_d) or '').strip() if col_d and col_d!='(skip)' else ''
            copy  =(row.get(col_c) or '').strip() if col_c and col_c!='(skip)' else ''

            if title: cmd+=[f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd+=[f'-Keywords={kw}',f'-Subject={kw}']
            if desc: cmd+=[f'-Description={desc}',f'-Caption-Abstract={desc}']
            if copy: cmd+=[f'-Copyright={copy}',f'-CopyrightNotice={copy}',f'-Rights={copy}']
            cmd.append(filepath)

            try:
                flags = subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                result = subprocess.run(cmd, capture_output=True, text=True,
                    timeout=30, creationflags=flags)
                actual = os.path.basename(filepath)
                if result.returncode==0:
                    ok+=1
                    self.root.after(0,lambda fn=actual: self.log(f'✓  {fn}','ok'))
                else:
                    errors+=1
                    err=(result.stderr or result.stdout or 'Unknown').strip()
                    self.root.after(0,lambda fn=actual,e=err:
                        self.log(f'✗  {fn}  —  {e}','err'))
            except Exception as ex:
                errors+=1
                self.root.after(0,lambda fn=filename,e=str(ex):
                    self.log(f'✗  {fn}  —  {e}','err'))

            self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                self._prog(n,t,o,s,e))

        summary=(f'● Done — {ok} embedded · {skipped} not found · {errors} errors')
        self.root.after(0, lambda: (
            self.log(summary,'info'),
            self.set_status(summary, BLUE),
            self.embed_btn.configure(state='normal',text='▶  Embed Metadata Now'),
            setattr(self,'running',False)
        ))

    def _prog(self, n, total, ok, skipped, errors):
        self.sb_progress.configure(value=n)
        self.set_status(f'Processing {n} of {total}…', BLUE)
        self.pill_ok.configure(text=f'{ok} embedded')
        self.pill_warn.configure(text=f'{skipped} not found')
        self.pill_err.configure(text=f'{errors} errors')

if __name__=='__main__':
    root = tk.Tk()
    app = MetadataApp(root)
    root.mainloop()
