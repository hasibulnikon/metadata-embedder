import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, subprocess, os, sys, threading, datetime, json

# ── ExifTool finder ────────────────────────────────────────────────────
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

def get_prefs_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'prefs.json')

def load_prefs():
    try:
        with open(get_prefs_path()) as f:
            return json.load(f)
    except Exception:
        return {'recent_csv': [], 'recent_folders': []}

def save_prefs(prefs):
    try:
        with open(get_prefs_path(), 'w') as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass

def add_recent(prefs, key, value, limit=5):
    lst = prefs.get(key, [])
    if value in lst: lst.remove(value)
    lst.insert(0, value)
    prefs[key] = lst[:limit]
    save_prefs(prefs)

# ── Colors ─────────────────────────────────────────────────────────────
BG   = '#141412'; BG2  = '#1a1a18'; BG3  = '#222220'; BG4  = '#0e0e0c'
TEXT = '#e8e8e4'; TEXT2= '#9a9a96'; TEXT3= '#4a4a48'
GRN  = '#4caf72'; GRN2 = '#1a3020'; GRN3 = '#2a4830'
GRN_BTN = '#2d7a4f'; GRN_BTN2= '#1e5c3a'
RED  = '#e87070'; RED2 = '#2a1a1a'; RED3 = '#4a2828'
AMB  = '#f0c060'; AMB2 = '#2a2010'; AMB3 = '#4a3818'
BLU  = '#3b8fe8'
BDR  = '#2a2a28'; BDR2 = '#3a3a38'

TOOLTIPS = {
    'FILENAME *': 'Column containing the image filename e.g. photo1.jpg — extension can differ from actual file',
    'TITLE':      'Short descriptive title shown in Adobe Stock search (max 200 chars)',
    'KEYWORDS':   'Comma or semicolon separated keywords (7–50 recommended for Adobe Stock)',
    'DESCRIPTION':'Longer caption or description of the image content',
    'COPYRIGHT':  'Copyright notice e.g. © 2026 Your Name',
}

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tip = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)
    def show(self, _=None):
        if self.tip: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f'+{x}+{y}')
        tk.Label(self.tip, text=self.text, font=('Segoe UI',8),
            bg='#2a2a28', fg=TEXT, padx=8, pady=4,
            wraplength=280, justify='left',
            highlightbackground=BDR2, highlightthickness=1).pack()
    def hide(self, _=None):
        if self.tip: self.tip.destroy(); self.tip=None

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Metadata Embedder")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.csv_path    = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.col_file    = tk.StringVar()
        self.col_title   = tk.StringVar()
        self.col_kw      = tk.StringVar()
        self.col_desc    = tk.StringVar()
        self.col_copy    = tk.StringVar()
        self.dry_run     = tk.BooleanVar(value=False)
        self.csv_headers = []
        self.csv_rows    = []
        self.running     = False
        self.log_visible = False
        self.last_summary= ''
        self.last_folder = ''
        self.prefs       = load_prefs()

        self._load_icon_img()
        self.build_ui()

        # Set window size after build
        self.root.update_idletasks()
        self._set_win(660, 580, center=True)
        self.check_exiftool()

    def _load_icon_img(self):
        self.icon_img = None
        base = sys._MEIPASS if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
        for n in ['icon.ico','app.ico']:
            p = os.path.join(base, n)
            if os.path.exists(p):
                try:
                    self.root.iconbitmap(p)
                    # Load as PhotoImage for titlebar
                    img = tk.PhotoImage(file=p) if p.endswith('.png') else None
                    self.icon_img = img
                except Exception:
                    pass
                break

    def _set_win(self, w, h, center=False):
        if center:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw-w)//2; y = (sh-h)//2
            self.root.geometry(f'{w}x{h}+{x}+{y}')
        else:
            cx = self.root.winfo_x(); cy = self.root.winfo_y()
            self.root.geometry(f'{w}x{h}+{cx}+{cy}')

    def ts(self):
        return datetime.datetime.now().strftime('%H:%M:%S')

    # ── UI BUILD ───────────────────────────────────────────────────────
    def build_ui(self):
        s = ttk.Style(); s.theme_use('clam')
        s.configure('TCombobox', fieldbackground=BG3, background=BG3,
            foreground=TEXT, selectbackground=BLU, arrowcolor=TEXT2, bordercolor=BDR)
        s.map('TCombobox', fieldbackground=[('readonly',BG3)],
            foreground=[('readonly',TEXT)], bordercolor=[('focus',BLU)])
        s.configure('Vertical.TScrollbar', background=BG3,
            troughcolor=BG2, arrowcolor=TEXT3, bordercolor=BDR)
        s.configure('green.Horizontal.TProgressbar',
            background=GRN, troughcolor=BG3, bordercolor=BDR)

        # ── Titlebar ───────────────────────────────────────────────────
        tbar = tk.Frame(self.root, bg=BG4, padx=12, pady=8)
        tbar.pack(fill='x')

        # Icon placeholder (M or actual icon)
        self.icon_lbl = tk.Label(tbar, text=" M ", font=('Segoe UI',10,'bold'),
            bg=GRN_BTN, fg='white', padx=4, pady=2)
        self.icon_lbl.pack(side='left')

        tk.Label(tbar, text="  Stock Metadata Embedder",
            font=('Segoe UI',12,'bold'), bg=BG4, fg=TEXT).pack(side='left')
        tk.Label(tbar, text=" v1.9", font=('Segoe UI',9),
            bg=BG4, fg=TEXT3).pack(side='left', padx=4)

        # Right side of titlebar
        tk.Label(tbar, text="© HASIBNIKON", font=('Segoe UI',8,'bold'),
            bg=BG4, fg=TEXT3).pack(side='right', padx=(6,0))
        tk.Frame(tbar, bg=BDR, width=1).pack(side='right', fill='y', padx=6)
        tk.Button(tbar, text='↺ Reset', command=self.reset_all,
            font=('Segoe UI',8,'bold'), bg=RED2, fg=RED,
            relief='flat', padx=8, pady=3, cursor='hand2',
            activebackground=RED3, activeforeground='#ffaaaa').pack(side='right')

        # ── Main body ──────────────────────────────────────────────────
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill='both', expand=True)

        # Left panel
        left_wrap = tk.Frame(self.body, bg=BG, width=430)
        left_wrap.pack(side='left', fill='y')
        left_wrap.pack_propagate(False)

        cv = tk.Canvas(left_wrap, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(left_wrap, orient='vertical', command=cv.yview)
        self.left = tk.Frame(cv, bg=BG, padx=10, pady=6)
        self.left.bind('<Configure>', lambda e: cv.configure(
            scrollregion=cv.bbox('all')))
        cv.create_window((0,0), window=self.left, anchor='nw', width=420)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        cv.pack(side='left', fill='both', expand=True)
        cv.bind_all('<MouseWheel>', lambda e: cv.yview_scroll(
            int(-1*(e.delta/120)),'units'))

        self.build_step1()
        self.build_step2()
        self.build_step3()
        self.build_embed_row()

        # Arrow toggle strip
        self.toggle_strip = tk.Frame(self.body, bg=BG3, width=18,
            cursor='hand2')
        self.toggle_strip.pack(side='left', fill='y')
        self.toggle_strip.pack_propagate(False)
        self.arrow_lbl = tk.Label(self.toggle_strip, text='»',
            font=('Segoe UI',11,'bold'), bg=BG3, fg=TEXT3,
            cursor='hand2')
        self.arrow_lbl.place(relx=0.5, rely=0.5, anchor='center')
        self.toggle_strip.bind('<Button-1>', lambda e: self.toggle_log())
        self.arrow_lbl.bind('<Button-1>', lambda e: self.toggle_log())
        Tooltip(self.toggle_strip, 'Click to show/hide activity log')

        # Right log panel (hidden by default)
        self.right_outer = tk.Frame(self.body, bg=BG2,
            highlightbackground=BDR, highlightthickness=1)
        self.build_log_panel()

        # Status bar
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
            bg=GRN_BTN, fg='white').pack(side='left')
        tk.Label(hdr, text=f"  {title}", font=('Segoe UI',9,'bold'),
            bg=BG3, fg=TEXT2).pack(side='left')
        tk.Frame(inner, bg=BDR, height=1).pack(fill='x')
        body = tk.Frame(inner, bg=BG2, padx=12, pady=10)
        body.pack(fill='x')
        return body

    def lbl(self, parent, text):
        tk.Label(parent, text=text, font=('Segoe UI',8,'bold'),
            bg=BG2, fg=TEXT3, anchor='w').pack(fill='x', pady=(4,2))

    def entry(self, parent, var):
        e = tk.Entry(parent, textvariable=var, font=('Segoe UI',10),
            bg=BG3, fg=TEXT, relief='flat', state='readonly',
            readonlybackground=BG3, insertbackground=TEXT,
            highlightbackground=BDR, highlightthickness=1)
        e.pack(fill='x', pady=(0,5), ipady=3)
        return e

    def bbtn(self, parent, text, cmd, full=True):
        b = tk.Button(parent, text=text, command=cmd,
            font=('Segoe UI',9,'bold'), bg=BG3, fg=GRN,
            relief='flat', padx=8, pady=5, cursor='hand2',
            activebackground=BDR2, activeforeground=GRN,
            highlightbackground=BDR, highlightthickness=1)
        if full: b.pack(fill='x', pady=(0,2))
        return b

    def build_step1(self):
        body = self.card('Load CSV', '1')
        self.lbl(body, 'CSV FILE')

        # Recent CSV dropdown row
        rec_row = tk.Frame(body, bg=BG2)
        rec_row.pack(fill='x', pady=(0,4))
        self.entry(rec_row, self.csv_path)

        rec_btn = tk.Menubutton(rec_row, text='▾', font=('Segoe UI',9,'bold'),
            bg=BG3, fg=TEXT2, relief='flat', padx=6, pady=5,
            activebackground=BDR2)
        rec_btn.pack(side='right', padx=(4,0))
        self.csv_recent_menu = tk.Menu(rec_btn, tearoff=0,
            bg=BG3, fg=TEXT, activebackground=BLU, activeforeground='white')
        rec_btn.configure(menu=self.csv_recent_menu)
        self._refresh_csv_recent()

        self.bbtn(body, '  Browse CSV…', self.load_csv)
        self.csv_info = tk.Label(body, text='', font=('Segoe UI',9),
            bg=BG2, fg=GRN, anchor='w')
        self.csv_info.pack(fill='x')

    def build_step2(self):
        body = self.card('Map columns', '2')
        note = tk.Label(body, text='Auto-detected from column names. Hover for field info.',
            font=('Segoe UI',8), bg=BG2, fg=TEXT3, anchor='w')
        note.pack(fill='x', pady=(0,8))

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
            col=i%2; row_n=i//2
            cell = tk.Frame(grid, bg=BG2, padx=3, pady=3)
            cell.grid(row=row_n, column=col, sticky='ew', padx=3)
            grid.columnconfigure(col, weight=1)
            lbl_w = tk.Label(cell, text=label, font=('Segoe UI',8,'bold'),
                bg=BG2, fg=TEXT3, anchor='w', cursor='question_arrow')
            lbl_w.pack(fill='x')
            Tooltip(lbl_w, TOOLTIPS.get(label,''))
            cb = ttk.Combobox(cell, textvariable=var,
                state='readonly', font=('Segoe UI',9))
            cb.pack(fill='x', pady=(2,0), ipady=2)
            self.col_combos[label] = cb

        # Validate button
        self.bbtn(body, '  Validate CSV', self.validate_csv)

    def build_step3(self):
        body = self.card('Image folder', '3')
        self.lbl(body, 'FOLDER PATH')

        rec_row = tk.Frame(body, bg=BG2)
        rec_row.pack(fill='x', pady=(0,4))
        self.entry(rec_row, self.folder_path)

        rec_btn2 = tk.Menubutton(rec_row, text='▾', font=('Segoe UI',9,'bold'),
            bg=BG3, fg=TEXT2, relief='flat', padx=6, pady=5,
            activebackground=BDR2)
        rec_btn2.pack(side='right', padx=(4,0))
        self.folder_recent_menu = tk.Menu(rec_btn2, tearoff=0,
            bg=BG3, fg=TEXT, activebackground=BLU, activeforeground='white')
        rec_btn2.configure(menu=self.folder_recent_menu)
        self._refresh_folder_recent()

        self.bbtn(body, '  Browse folder…', self.browse_folder)

        # Match counter badge
        self.match_badge = tk.Label(body, text='',
            font=('Segoe UI',9,'bold'), bg=BG2, fg=TEXT3, anchor='w')
        self.match_badge.pack(fill='x', pady=(4,0))

        # Open folder button (hidden until batch done)
        self.open_folder_btn = tk.Button(body, text='  Open folder in Explorer',
            command=self.open_folder,
            font=('Segoe UI',9,'bold'), bg=BG3, fg=TEXT2,
            relief='flat', padx=8, pady=5, cursor='hand2',
            activebackground=BDR2)
        # not packed yet

    def build_embed_row(self):
        row = tk.Frame(self.left, bg=BG, pady=6)
        row.pack(fill='x')

        # Dry run toggle
        dry = tk.Checkbutton(row, text='Dry run',
            variable=self.dry_run,
            font=('Segoe UI',9), bg=BG, fg=TEXT2,
            selectcolor=BG3, activebackground=BG,
            activeforeground=TEXT, cursor='hand2')
        dry.pack(side='left', padx=(0,8))
        Tooltip(dry, 'Simulate embedding without writing to files — use to test before running for real')

        self.embed_btn = tk.Button(row, text='▶  Embed Metadata Now',
            command=self.start_embed,
            font=('Segoe UI',12,'bold'), bg=GRN_BTN, fg='white',
            relief='flat', padx=0, pady=11, cursor='hand2',
            activebackground=GRN_BTN2, activeforeground='white')
        self.embed_btn.pack(side='left', fill='x', expand=True)

        # Export log button
        tk.Button(row, text='↓', command=self.export_log,
            font=('Segoe UI',10,'bold'), bg=BG3, fg=TEXT2,
            relief='flat', padx=8, pady=11, cursor='hand2',
            activebackground=BDR2).pack(side='left', padx=(6,0))
        Tooltip(row, 'Export activity log to TXT file')

    def build_log_panel(self):
        hdr = tk.Frame(self.right_outer, bg=BG3)
        hdr.pack(fill='x')
        tk.Frame(hdr, bg=BDR, height=1).pack(fill='x', side='bottom')
        ih = tk.Frame(hdr, bg=BG3, padx=10, pady=7)
        ih.pack(fill='x')
        tk.Label(ih, text='Activity Log', font=('Segoe UI',9,'bold'),
            bg=BG3, fg=TEXT3).pack(side='left')
        tk.Button(ih, text='Clear', command=self.clear_log,
            font=('Segoe UI',8), bg=BG4, fg=TEXT3,
            relief='flat', padx=6, pady=2, cursor='hand2').pack(side='right')

        lf = tk.Frame(self.right_outer, bg=BG2)
        lf.pack(fill='both', expand=True)
        self.log_text = tk.Text(lf, font=('Consolas',9),
            bg=BG2, fg=TEXT, relief='flat', state='disabled',
            wrap='word', padx=8, pady=6, width=32)
        sb2 = ttk.Scrollbar(lf, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb2.set)
        sb2.pack(side='right', fill='y')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('ok',   foreground=GRN)
        self.log_text.tag_config('warn', foreground=AMB)
        self.log_text.tag_config('err',  foreground=RED)
        self.log_text.tag_config('info', foreground=BLU)
        self.log_text.tag_config('ts',   foreground=TEXT3)

    def toggle_log(self):
        if self.log_visible:
            self.right_outer.pack_forget()
            self.log_visible = False
            self.arrow_lbl.configure(text='»')
            self._set_win(470, 580)
        else:
            self.right_outer.pack(side='left', fill='both', expand=True,
                padx=(0,0), pady=0)
            self.log_visible = True
            self.arrow_lbl.configure(text='«')
            self._set_win(760, 580)

    def build_statusbar(self):
        sb = tk.Frame(self.root, bg=BG4,
            highlightbackground=BDR, highlightthickness=1)
        sb.pack(fill='x', side='bottom')
        inner = tk.Frame(sb, bg=BG4, padx=10, pady=5)
        inner.pack(fill='x')

        self.sb_status = tk.Label(inner, text='Ready',
            font=('Segoe UI',9), bg=BG4, fg=TEXT3, anchor='w')
        self.sb_status.pack(side='left')

        self.sb_et = tk.Label(inner, text='ExifTool · checking…',
            font=('Segoe UI',8), bg=BG4, fg=TEXT3)
        self.sb_et.pack(side='right')

        self.sb_prog = ttk.Progressbar(inner, mode='determinate',
            length=90, style='green.Horizontal.TProgressbar')
        self.sb_prog.pack(side='right', padx=(0,10))

        pf = tk.Frame(inner, bg=BG4)
        pf.pack(side='left', padx=(12,0))
        self.p_ok   = self._pill(pf, '0 embedded', GRN2, GRN,  GRN3)
        self.p_warn = self._pill(pf, '0 not found', AMB2, AMB, AMB3)
        self.p_err  = self._pill(pf, '0 errors',   RED2, RED,  RED3)

    def _pill(self, parent, text, bg, fg, bdr):
        l = tk.Label(parent, text=text, font=('Segoe UI',8,'bold'),
            bg=bg, fg=fg, padx=7, pady=2,
            highlightbackground=bdr, highlightthickness=1)
        l.pack(side='left', padx=2)
        return l

    def set_status(self, msg, fg=None):
        self.sb_status.configure(text=msg, fg=fg or TEXT3)

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
            self.log('✓  ExifTool ready','ok')
            self.sb_et.configure(text='ExifTool · ready', fg=GRN)
        else:
            self.log('⚠  ExifTool not found','warn')
            self.sb_et.configure(text='ExifTool · missing', fg=RED)

    # ── Recent menus ───────────────────────────────────────────────────
    def _refresh_csv_recent(self):
        self.csv_recent_menu.delete(0,'end')
        for p in self.prefs.get('recent_csv',[]):
            self.csv_recent_menu.add_command(label=os.path.basename(p),
                command=lambda v=p: self._load_csv_path(v))
        if not self.prefs.get('recent_csv'):
            self.csv_recent_menu.add_command(label='No recent files',state='disabled')

    def _refresh_folder_recent(self):
        self.folder_recent_menu.delete(0,'end')
        for p in self.prefs.get('recent_folders',[]):
            self.folder_recent_menu.add_command(label=p,
                command=lambda v=p: self._set_folder(v))
        if not self.prefs.get('recent_folders'):
            self.folder_recent_menu.add_command(label='No recent folders',state='disabled')

    # ── CSV ────────────────────────────────────────────────────────────
    def load_csv(self):
        path = filedialog.askopenfilename(title='Select metadata CSV',
            filetypes=[('CSV files','*.csv'),('All files','*.*')])
        if not path: return
        self._load_csv_path(path)

    def _load_csv_path(self, path):
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.csv_rows = list(reader)
                self.csv_headers = list(reader.fieldnames or [])
            self.csv_path.set(path)
            self.csv_info.configure(
                text=f'✓  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns', fg=GRN)
            self.log(f'✓  CSV loaded — {len(self.csv_rows)} rows · {os.path.basename(path)}','ok')
            self.set_status(f'CSV loaded: {len(self.csv_rows)} rows', GRN)
            add_recent(self.prefs, 'recent_csv', path)
            self._refresh_csv_recent()
            self.update_combos()
            self._update_match_badge()
        except Exception as e:
            messagebox.showerror('CSV Error', str(e))

    def update_combos(self):
        opts = ['(skip)'] + self.csv_headers
        hints = {
            'FILENAME *': ['filename','file','name','image'],
            'TITLE':      ['title'],
            'KEYWORDS':   ['keyword','tag','kw'],
            'DESCRIPTION':['desc','caption','description'],
            'COPYRIGHT':  ['copy','copyright','rights'],
        }
        vmap = {
            'FILENAME *': self.col_file,  'TITLE': self.col_title,
            'KEYWORDS':   self.col_kw,    'DESCRIPTION': self.col_desc,
            'COPYRIGHT':  self.col_copy,
        }
        for label, cb in self.col_combos.items():
            cb['values'] = opts
            g = next((c for h in hints.get(label,[])
                for c in self.csv_headers if h in c.lower()),'')
            vmap[label].set(g or '(skip)')

    def validate_csv(self):
        if not self.csv_rows:
            messagebox.showinfo('Validate','Load a CSV first.'); return
        col_k = self.col_kw.get()
        col_t = self.col_title.get()
        issues = []
        for i, row in enumerate(self.csv_rows, 1):
            kw = (row.get(col_k) or '') if col_k and col_k!='(skip)' else ''
            title = (row.get(col_t) or '') if col_t and col_t!='(skip)' else ''
            kw_list = [k.strip() for k in kw.replace(';',',').split(',') if k.strip()] if kw else []
            fn = row.get(self.col_file.get() or '','') or ''
            if not fn.strip():
                issues.append(f'Row {i}: empty filename')
            if title and len(title) > 200:
                issues.append(f'Row {i}: title too long ({len(title)} chars)')
            if kw_list and len(kw_list) < 7:
                issues.append(f'Row {i}: only {len(kw_list)} keywords (min 7 recommended)')
            if kw_list and len(kw_list) > 50:
                issues.append(f'Row {i}: {len(kw_list)} keywords (max 50 for Adobe Stock)')
        if issues:
            msg = f'{len(issues)} issue(s) found:\n\n' + '\n'.join(issues[:20])
            if len(issues) > 20: msg += f'\n…and {len(issues)-20} more'
            messagebox.showwarning('CSV Validation', msg)
            self.log(f'⚠  CSV validation: {len(issues)} issues found','warn')
        else:
            messagebox.showinfo('CSV Validation','✓ All rows look good!')
            self.log('✓  CSV validation passed','ok')

    # ── Folder ─────────────────────────────────────────────────────────
    def browse_folder(self):
        path = filedialog.askdirectory(title='Select image folder')
        if path: self._set_folder(path)

    def _set_folder(self, path):
        self.folder_path.set(path)
        self.last_folder = path
        add_recent(self.prefs, 'recent_folders', path)
        self._refresh_folder_recent()
        self._update_match_badge()
        self.log(f'✓  Folder set — {path}','ok')
        self.set_status('Folder loaded', GRN)

    def _update_match_badge(self):
        folder = self.folder_path.get()
        col_f  = self.col_file.get()
        if not folder or not self.csv_rows or not col_f or col_f=='(skip)':
            self.match_badge.configure(text='')
            return
        matched = sum(1 for row in self.csv_rows
            if find_file_any_ext(folder, (row.get(col_f) or '').strip()))
        total = len(self.csv_rows)
        color = GRN if matched==total else AMB if matched>0 else RED
        self.match_badge.configure(
            text=f'  {matched} of {total} files matched in folder', fg=color)

    def open_folder(self):
        f = self.last_folder or self.folder_path.get()
        if f and os.path.exists(f):
            os.startfile(f)

    # ── Reset ──────────────────────────────────────────────────────────
    def reset_all(self):
        if self.running:
            messagebox.showwarning('Busy','Wait for current job to finish.'); return
        if not messagebox.askyesno('Reset','Clear everything and start fresh?\n\nLast run summary will be kept in status bar.'): return
        for v in [self.csv_path,self.folder_path,self.col_file,
                  self.col_title,self.col_kw,self.col_desc,self.col_copy]:
            v.set('')
        self.csv_headers=[]; self.csv_rows=[]
        self.csv_info.configure(text='')
        self.match_badge.configure(text='')
        for cb in self.col_combos.values(): cb['values']=[]
        self.sb_prog.configure(value=0)
        self.p_ok.configure(text='0 embedded')
        self.p_warn.configure(text='0 not found')
        self.p_err.configure(text='0 errors')
        self.embed_btn.configure(state='normal', text='▶  Embed Metadata Now')
        self.open_folder_btn.pack_forget()
        self.clear_log()
        self.log('↺  Reset — ready for new batch','info')
        if self.last_summary:
            self.set_status(f'Last run: {self.last_summary}', TEXT3)
        else:
            self.set_status('Ready', TEXT3)

    # ── Export log ─────────────────────────────────────────────────────
    def export_log(self):
        content = self.log_text.get('1.0','end').strip()
        if not content:
            messagebox.showinfo('Export Log','Log is empty.'); return
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text files','*.txt'),('All files','*.*')],
            initialfile=f'embed_log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        if path:
            with open(path,'w',encoding='utf-8') as f:
                f.write(content)
            self.log(f'✓  Log exported → {os.path.basename(path)}','ok')

    # ── Embed ──────────────────────────────────────────────────────────
    def start_embed(self):
        if self.running: return
        et = find_exiftool()
        if not et:
            messagebox.showerror('ExifTool not found',
                'Place exiftool.exe in the same folder as this app.\nhttps://exiftool.org')
            return
        if not self.csv_rows:
            messagebox.showerror('No CSV','Load a CSV first.'); return
        if not self.folder_path.get():
            messagebox.showerror('No folder','Select the image folder.'); return
        fc = self.col_file.get()
        if not fc or fc=='(skip)':
            messagebox.showerror('Column missing','Select the filename column.'); return
        dry = self.dry_run.get()
        if dry and not messagebox.askyesno('Dry Run',
            'Dry run mode: files will NOT be modified.\nContinue?'): return
        self.running=True
        self.embed_btn.configure(state='disabled',
            text='Dry run…' if dry else 'Processing…')
        threading.Thread(target=self.run_embed, args=(et, dry), daemon=True).start()

    def run_embed(self, et, dry):
        folder=self.folder_path.get()
        col_f=self.col_file.get(); col_t=self.col_title.get()
        col_k=self.col_kw.get();   col_d=self.col_desc.get()
        col_c=self.col_copy.get()
        total=len(self.csv_rows)
        ok=skipped=errors=0
        not_found_files=[]

        self.root.after(0,lambda: self.sb_prog.configure(maximum=total,value=0))
        self.root.after(0,lambda: self.log(
            f'{"[DRY RUN] " if dry else ""}▶  Batch started — {total} rows','info'))

        for i, row in enumerate(self.csv_rows):
            filename=(row.get(col_f) or '').strip()
            if not filename:
                skipped+=1
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue

            filepath=find_file_any_ext(folder, filename)
            if not filepath:
                not_found_files.append(filename)
                skipped+=1
                self.root.after(0,lambda fn=filename:
                    self.log(f'⚠  Not found: {fn}','warn'))
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue

            if dry:
                ok+=1
                actual=os.path.basename(filepath)
                self.root.after(0,lambda fn=actual:
                    self.log(f'[DRY] ✓  {fn}','ok'))
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue

            cmd=[et,'-overwrite_original','-codedcharacterset=UTF8']
            title=(row.get(col_t) or '').strip() if col_t and col_t!='(skip)' else ''
            kw_raw=(row.get(col_k) or '').strip() if col_k and col_k!='(skip)' else ''
            desc=(row.get(col_d) or '').strip() if col_d and col_d!='(skip)' else ''
            copy=(row.get(col_c) or '').strip() if col_c and col_c!='(skip)' else ''

            if title: cmd+=[f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd+=[f'-Keywords={kw}',f'-Subject={kw}']
            if desc:  cmd+=[f'-Description={desc}',f'-Caption-Abstract={desc}']
            if copy:  cmd+=[f'-Copyright={copy}',f'-CopyrightNotice={copy}',f'-Rights={copy}']
            cmd.append(filepath)

            try:
                flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                res=subprocess.run(cmd,capture_output=True,text=True,
                    timeout=30,creationflags=flags)
                actual=os.path.basename(filepath)
                if res.returncode==0:
                    ok+=1
                    self.root.after(0,lambda fn=actual: self.log(f'✓  {fn}','ok'))
                else:
                    errors+=1
                    err=(res.stderr or res.stdout or 'Unknown').strip()
                    self.root.after(0,lambda fn=actual,e=err:
                        self.log(f'✗  {fn}  —  {e}','err'))
            except Exception as ex:
                errors+=1
                self.root.after(0,lambda fn=filename,e=str(ex):
                    self.log(f'✗  {fn}  —  {e}','err'))

            self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                self._prog(n,t,o,s,e))

        prefix='[DRY RUN] ' if dry else ''
        summary=(f'{prefix}{ok} embedded · {skipped} not found · {errors} errors')
        self.last_summary = summary
        self.root.after(0,lambda: (
            self.log(f'● {summary}','info'),
            self.set_status(f'Done — {summary}', GRN),
            self.embed_btn.configure(state='normal',text='▶  Embed Metadata Now'),
            self.open_folder_btn.pack(fill='x', pady=(6,0)),
            setattr(self,'running',False)
        ))

    def _prog(self, n, total, ok, skipped, errors):
        self.sb_prog.configure(value=n)
        self.set_status(f'Processing {n} of {total}…', BLU)
        self.p_ok.configure(text=f'{ok} embedded')
        self.p_warn.configure(text=f'{skipped} not found')
        self.p_err.configure(text=f'{errors} errors')

if __name__=='__main__':
    root=tk.Tk()
    app=MetadataApp(root)
    root.mainloop()
