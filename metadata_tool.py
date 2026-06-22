import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, subprocess, os, sys, threading, datetime, json

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
    except: pass
    return None

def get_prefs_path():
    base = os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'prefs.json')

def load_prefs():
    try:
        with open(get_prefs_path()) as f: return json.load(f)
    except: return {'recent_csv':[], 'recent_folders':[]}

def save_prefs(p):
    try:
        with open(get_prefs_path(),'w') as f: json.dump(p,f,indent=2)
    except: pass

def add_recent(prefs, key, value, limit=5):
    lst = prefs.get(key,[])
    if value in lst: lst.remove(value)
    lst.insert(0, value)
    prefs[key] = lst[:limit]
    save_prefs(prefs)

BG='#141412'; BG2='#1a1a18'; BG3='#222220'; BG4='#0e0e0c'
TEXT='#e8e8e4'; TEXT2='#9a9a96'; TEXT3='#4a4a48'
GRN='#4caf72'; GRN2='#1a3020'; GRN3='#2a4830'
GRNB='#2d7a4f'; GRNB2='#1e5c3a'
RED='#e87070'; RED2='#2a1a1a'; RED3='#4a2828'
AMB='#f0c060'; AMB2='#2a2010'; AMB3='#4a3818'
BLU='#3b8fe8'
BDR='#2a2a28'; BDR2='#3a3a38'

TIPS = {
    'FILENAME':  'Column with image filename. Extension can differ from actual file on disk.',
    'TITLE':     'Short descriptive title shown in Adobe Stock (max 200 chars).',
    'KEYWORDS':  'Comma or semicolon separated. 7–50 keywords recommended for Adobe Stock.',
    'DESCRIPTION':'Longer caption or description of the image content.',
}

class Tip:
    def __init__(self, w, text):
        self.w=w; self.text=text; self.tip=None
        w.bind('<Enter>', self.show); w.bind('<Leave>', self.hide)
    def show(self,_=None):
        if self.tip: return
        x=self.w.winfo_rootx()+20; y=self.w.winfo_rooty()+self.w.winfo_height()+4
        self.tip=tk.Toplevel(self.w); self.tip.wm_overrideredirect(True)
        self.tip.geometry(f'+{x}+{y}')
        tk.Label(self.tip,text=self.text,font=('Segoe UI',8),bg='#2a2a28',fg=TEXT,
            padx=8,pady=4,wraplength=260,justify='left',
            highlightbackground=BDR2,highlightthickness=1).pack()
    def hide(self,_=None):
        if self.tip: self.tip.destroy(); self.tip=None

class App:
    def __init__(self, root):
        self.root=root
        self.root.title("Meta Zone")
        self.root.configure(bg=BG)
        self.root.resizable(True,True)
        self.log_visible=False
        self.running=False
        self.last_summary=''
        self.last_folder=''
        self.prefs=load_prefs()
        self.csv_path=tk.StringVar()
        self.folder_path=tk.StringVar()
        self.col_file=tk.StringVar()
        self.col_title=tk.StringVar()
        self.col_kw=tk.StringVar()
        self.col_desc=tk.StringVar()
        self.csv_headers=[]
        self.csv_rows=[]
        self._load_app_icon()
        self._style()
        self._build()
        self.root.update_idletasks()
        self._center(560, 600)
        self.root.minsize(420,500)
        self.check_et()

    def _load_app_icon(self):
        base = sys._MEIPASS if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
        self.icon_photo = None
        for n in ['icon.ico','icon.png','app.ico']:
            p = os.path.join(base, n)
            if os.path.exists(p):
                try: self.root.iconbitmap(p)
                except: pass
                try:
                    img = tk.PhotoImage(file=p)
                    self.icon_photo = img
                except: pass
                break

    def _style(self):
        s=ttk.Style(); s.theme_use('clam')
        s.configure('TCombobox',fieldbackground=BG3,background=BG3,
            foreground=TEXT,selectbackground=BLU,arrowcolor=TEXT2,bordercolor=BDR)
        s.map('TCombobox',fieldbackground=[('readonly',BG3)],
            foreground=[('readonly',TEXT)],bordercolor=[('focus',BLU)])
        s.configure('Vertical.TScrollbar',background=BG3,
            troughcolor=BG2,arrowcolor=TEXT3,bordercolor=BDR)
        s.configure('G.Horizontal.TProgressbar',
            background=GRN,troughcolor=BG3,bordercolor=BDR)

    def _center(self, w, h):
        sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight()
        x=(sw-w)//2; y=(sh-h)//2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _resize(self, w):
        cx=self.root.winfo_x(); cy=self.root.winfo_y()
        h=self.root.winfo_height()
        self.root.geometry(f'{w}x{h}+{cx}+{cy}')

    def ts(self): return datetime.datetime.now().strftime('%H:%M:%S')

    def _build(self):
        # Titlebar
        tb=tk.Frame(self.root,bg=BG4,padx=12,pady=8)
        tb.pack(fill='x')
        # Icon label
        if self.icon_photo:
            il=tk.Label(tb,image=self.icon_photo,bg=BG4)
        else:
            il=tk.Label(tb,text=" M ",font=('Segoe UI',10,'bold'),bg=GRNB,fg='white',padx=3,pady=1)
        il.pack(side='left')
        tk.Label(tb,text="  Meta Zone",font=('Segoe UI',14,'bold'),bg=BG4,fg=TEXT).pack(side='left')
        tk.Label(tb,text=" v2.0",font=('Segoe UI',9),bg=BG4,fg=TEXT3).pack(side='left',padx=2)
        right_credit=tk.Frame(tb,bg=BG4)
        right_credit.pack(side='right',padx=(4,0))
        tk.Label(right_credit,text="All Rights Reserved By",font=('Segoe UI',8),bg=BG4,fg=TEXT3).pack(anchor='e')
        tk.Label(right_credit,text="© HASIBNIKON",font=('Segoe UI',11,'bold'),bg=BG4,fg=TEXT2).pack(anchor='e')
        tk.Frame(tb,bg=BDR,width=1).pack(side='right',fill='y',padx=8)

        # Body
        self.body=tk.Frame(self.root,bg=BG)
        self.body.pack(fill='both',expand=True)
        self.body.columnconfigure(0,weight=1)
        self.body.rowconfigure(0,weight=1)

        # Left scrollable area
        left_wrap=tk.Frame(self.body,bg=BG)
        left_wrap.grid(row=0,column=0,sticky='nsew')
        left_wrap.rowconfigure(0,weight=1)
        left_wrap.columnconfigure(0,weight=1)

        self.canvas=tk.Canvas(left_wrap,bg=BG,highlightthickness=0)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        self.canvas.bind('<Configure>',self._on_canvas_resize)

        self.left=tk.Frame(self.canvas,bg=BG,padx=12,pady=8)
        self.left_win=self.canvas.create_window((0,0),window=self.left,anchor='nw')
        self.left.bind('<Configure>',lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        self.canvas.bind_all('<MouseWheel>',self._on_scroll)
        self.left.columnconfigure(0,weight=1)

        self._build_embed_row()
        self._build_csv()
        self._build_folder()
        self._build_map()
        self._build_scroll_btns(left_wrap)

        # Tab toggle button - centered strip between left and log
        # Center strip — scroll buttons perfectly centered
        self.tab_btn=tk.Frame(self.body,bg=BG,width=30)
        self.tab_btn.grid(row=0,column=1,sticky='ns')
        self.tab_btn.pack_propagate(False)
        self.tab_btn.grid_propagate(False)
        strip_inner=tk.Frame(self.tab_btn,bg=BG)
        strip_inner.place(relx=0.5,rely=0.5,anchor='center')
        self.up_btn=tk.Label(strip_inner,text='▲',font=('Segoe UI',9,'bold'),
            bg=BG3,fg=TEXT3,cursor='hand2',padx=5,pady=5,
            highlightbackground=BDR,highlightthickness=1)
        self.up_btn.pack(pady=(0,6))
        self.up_btn.bind('<Button-1>',lambda e: self.canvas.yview_scroll(-3,'units'))
        self.dn_btn=tk.Label(strip_inner,text='▼',font=('Segoe UI',9,'bold'),
            bg=BG3,fg=TEXT3,cursor='hand2',padx=5,pady=5,
            highlightbackground=BDR,highlightthickness=1)
        self.dn_btn.pack()
        self.dn_btn.bind('<Button-1>',lambda e: self.canvas.yview_scroll(3,'units'))

        # Log panel — 270px wide
        self.log_frame=tk.Frame(self.body,bg=BG2,width=270)
        self.log_frame.grid_propagate(False)
        self._build_log()

        # Status bar
        self._build_sbar()

    def _on_canvas_resize(self, e):
        self.canvas.itemconfig(self.left_win, width=e.width)

    def _on_scroll(self, e):
        self.canvas.yview_scroll(int(-1*(e.delta/120)),'units')

    def _build_scroll_btns(self, parent):
        # These go into the toggle_strip frame (column=1 in body grid)
        # They will be placed after the strip is created in _build()
        pass

    def card(self, num, title):
        outer=tk.Frame(self.left,bg=BG,pady=4)
        outer.pack(fill='x')
        outer.columnconfigure(0,weight=1)
        inner=tk.Frame(outer,bg=BG2,highlightbackground=BDR,highlightthickness=1)
        inner.pack(fill='x')
        inner.columnconfigure(0,weight=1)
        hdr=tk.Frame(inner,bg=BG3,padx=10,pady=7)
        hdr.pack(fill='x')
        hdr.columnconfigure(1,weight=1)
        tk.Label(hdr,text=f" {num} ",font=('Segoe UI',9,'bold'),bg=GRNB,fg='white').pack(side='left')
        tk.Label(hdr,text=f"  {title}",font=('Segoe UI',9,'bold'),bg=BG3,fg=TEXT2).pack(side='left')
        tk.Frame(inner,bg=BDR,height=1).pack(fill='x')
        body=tk.Frame(inner,bg=BG2,padx=12,pady=10)
        body.pack(fill='x')
        body.columnconfigure(0,weight=1)
        return body

    def lbl(self, p, t):
        tk.Label(p,text=t,font=('Segoe UI',8,'bold'),bg=BG2,fg=TEXT3,anchor='w').pack(fill='x',pady=(4,2))

    def inline_field(self, parent, var, browse_cmd, recent_menu_name):
        row=tk.Frame(parent,bg=BG2)
        row.pack(fill='x',pady=(0,6))
        row.columnconfigure(0,weight=1)
        e=tk.Entry(row,textvariable=var,font=('Segoe UI',9),
            bg=BG3,fg=TEXT,relief='flat',state='readonly',
            readonlybackground=BG3,highlightbackground=BDR,highlightthickness=1)
        e.grid(row=0,column=0,sticky='ew',ipady=4)
        btn=tk.Button(row,text='Browse',command=browse_cmd,
            font=('Segoe UI',9,'bold'),bg=GRNB,fg='white',
            relief='flat',padx=10,pady=4,cursor='hand2',
            activebackground=GRNB2,activeforeground='white')
        btn.grid(row=0,column=1,padx=(6,0))
        mb=tk.Menubutton(row,text='▾',font=('Segoe UI',9,'bold'),
            bg=BG3,fg=TEXT2,relief='flat',padx=6,pady=4,
            activebackground=BDR2,cursor='hand2')
        mb.grid(row=0,column=2,padx=(3,0))
        menu=tk.Menu(mb,tearoff=0,bg=BG3,fg=TEXT,
            activebackground=BLU,activeforeground='white')
        mb.configure(menu=menu)
        setattr(self,recent_menu_name,menu)
        return e

    def _build_embed_row(self):
        row=tk.Frame(self.left,bg=BG,pady=6)
        row.pack(fill='x')
        row.columnconfigure(0,weight=1)
        self.embed_btn=tk.Button(row,text='▶   Embed Metadata Now',
            command=self.start_embed,
            font=('Segoe UI',12,'bold'),bg=GRNB,fg='white',
            relief='flat',pady=12,cursor='hand2',
            activebackground=GRNB2,activeforeground='white')
        self.embed_btn.grid(row=0,column=0,sticky='ew')
        # Reset icon button
        self.reset_btn=tk.Button(row,text='↺',command=self.reset_all,
            font=('Segoe UI',13,'bold'),bg=RED2,fg=RED,
            relief='flat',padx=10,pady=11,cursor='hand2',
            activebackground=RED3,activeforeground='#ffaaaa',
            highlightbackground=RED3,highlightthickness=1)
        self.reset_btn.grid(row=0,column=1,padx=(6,0))
        Tip(self.reset_btn,'Reset all fields and start over')
        # Export log icon button
        self.export_btn=tk.Button(row,text='📄',command=self.export_log,
            font=('Segoe UI',13),bg=BG3,fg=TEXT2,
            relief='flat',padx=10,pady=11,cursor='hand2',
            activebackground=BDR2,activeforeground=TEXT,
            highlightbackground=BDR,highlightthickness=1)
        self.export_btn.grid(row=0,column=2,padx=(4,0))
        Tip(self.export_btn,'Export activity log to TXT file')

    def _build_csv(self):
        body=self.card('1','Load CSV')
        self.lbl(body,'CSV FILE')
        self.inline_field(body,self.csv_path,self.load_csv,'csv_recent_menu')
        self.csv_info=tk.Label(body,text='',font=('Segoe UI',9),bg=BG2,fg=GRN,anchor='w')
        self.csv_info.pack(fill='x')
        self._refresh_csv_recent()

    def _build_folder(self):
        body=self.card('2','Image folder')
        self.lbl(body,'FOLDER PATH')
        self.inline_field(body,self.folder_path,self.browse_folder,'folder_recent_menu')
        self.match_badge=tk.Label(body,text='',font=('Segoe UI',9,'bold'),bg=BG2,fg=TEXT3,anchor='w')
        self.match_badge.pack(fill='x')
        self.open_folder_btn=tk.Button(body,text='  Open folder in Explorer',
            command=self.open_folder,
            font=('Segoe UI',9,'bold'),bg=BG3,fg=TEXT2,
            relief='flat',padx=8,pady=5,cursor='hand2',
            activebackground=BDR2)
        self._refresh_folder_recent()

    def _build_map(self):
        body=self.card('3','Map columns')
        tk.Label(body,text='Auto-detected. Hover labels for info.',
            font=('Segoe UI',8),bg=BG2,fg=TEXT3,anchor='w').pack(fill='x',pady=(0,8))
        self.col_combos={}
        fields=[('FILENAME',self.col_file),('TITLE',self.col_title),
                ('KEYWORDS',self.col_kw),('DESCRIPTION',self.col_desc)]
        grid=tk.Frame(body,bg=BG2)
        grid.pack(fill='x')
        grid.columnconfigure(0,weight=1); grid.columnconfigure(1,weight=1)
        for i,(label,var) in enumerate(fields):
            col=i%2; row_n=i//2
            cell=tk.Frame(grid,bg=BG2,padx=3,pady=3)
            cell.grid(row=row_n,column=col,sticky='ew',padx=3)
            cell.columnconfigure(0,weight=1)
            lw=tk.Label(cell,text=label,font=('Segoe UI',8,'bold'),
                bg=BG2,fg=TEXT3,anchor='w',cursor='question_arrow')
            lw.pack(fill='x')
            Tip(lw,TIPS.get(label,''))
            cb=ttk.Combobox(cell,textvariable=var,state='readonly',font=('Segoe UI',9))
            cb.pack(fill='x',pady=(2,0),ipady=2)
            self.col_combos[label]=cb

    def _build_log(self):
        hdr=tk.Frame(self.log_frame,bg=BG3)
        hdr.pack(fill='x')
        tk.Frame(hdr,bg=BDR,height=1).pack(fill='x',side='bottom')
        ih=tk.Frame(hdr,bg=BG3,padx=10,pady=7)
        ih.pack(fill='x')
        tk.Label(ih,text='Activity Log',font=('Segoe UI',9,'bold'),bg=BG3,fg=TEXT3).pack(side='left')
        tk.Button(ih,text='Clear',command=self.clear_log,
            font=('Segoe UI',8),bg=BG4,fg=TEXT3,relief='flat',
            padx=6,pady=2,cursor='hand2').pack(side='right')
        lf=tk.Frame(self.log_frame,bg=BG2)
        lf.pack(fill='both',expand=True)
        self.log_text=tk.Text(lf,font=('Consolas',9),bg=BG2,fg=TEXT,
            relief='flat',state='disabled',wrap='word',padx=8,pady=6,width=28)
        sb=ttk.Scrollbar(lf,command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right',fill='y')
        self.log_text.pack(fill='both',expand=True)
        self.log_text.tag_config('ok',foreground=GRN)
        self.log_text.tag_config('warn',foreground=AMB)
        self.log_text.tag_config('err',foreground=RED)
        self.log_text.tag_config('info',foreground=BLU)
        self.log_text.tag_config('ts',foreground=TEXT3)

    def _build_sbar(self):
        sb=tk.Frame(self.root,bg=BG4,highlightbackground=BDR,highlightthickness=1)
        sb.pack(fill='x',side='bottom')
        inner=tk.Frame(sb,bg=BG4,padx=10,pady=5)
        inner.pack(fill='x')
        self.sb_status=tk.Label(inner,text='Ready',font=('Segoe UI',9),bg=BG4,fg=TEXT3,anchor='w')
        self.sb_status.pack(side='left')
        self.sb_et=tk.Label(inner,text='ExifTool · checking…',font=('Segoe UI',8),bg=BG4,fg=TEXT3)
        self.sb_et.pack(side='right')
        self.sb_prog=ttk.Progressbar(inner,mode='determinate',length=80,style='G.Horizontal.TProgressbar')
        self.sb_prog.pack(side='right',padx=(0,8))
        pf=tk.Frame(inner,bg=BG4)
        pf.pack(side='left',padx=(10,0))
        self.p_ok=self._pill(pf,'0 embedded',GRN2,GRN,GRN3)
        self.p_warn=self._pill(pf,'0 not found',AMB2,AMB,AMB3)
        self.p_err=self._pill(pf,'0 errors',RED2,RED,RED3)

    def _pill(self,parent,text,bg,fg,bdr):
        l=tk.Label(parent,text=text,font=('Segoe UI',8,'bold'),
            bg=bg,fg=fg,padx=7,pady=2,
            highlightbackground=bdr,highlightthickness=1)
        l.pack(side='left',padx=2)
        return l

    def toggle_log(self):
        if self.log_visible:
            self.log_frame.grid_forget()
            self.log_visible=False
            self.tab_btn.configure(text='»')
            self._resize(self.root.winfo_width()-215)
        else:
            self.log_frame.grid(row=0,column=2,sticky='nsew',padx=(0,0))
            self.log_visible=True
            self.tab_btn.configure(text='«')
            self._resize(self.root.winfo_width()+215)

    def set_status(self,msg,fg=None):
        self.sb_status.configure(text=msg,fg=fg or TEXT3)

    def log(self,msg,tag=''):
        self.log_text.configure(state='normal')
        self.log_text.insert('end',f'{self.ts()}  ','ts')
        self.log_text.insert('end',msg+'\n',tag)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0','end')
        self.log_text.configure(state='disabled')

    def check_et(self):
        et=find_exiftool()
        if et:
            self.log('✓  ExifTool ready','ok')
            self.sb_et.configure(text='ExifTool · ready',fg=GRN)
        else:
            self.log('⚠  ExifTool not found — place exiftool.exe next to this app','warn')
            self.sb_et.configure(text='ExifTool · missing',fg=RED)

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

    def load_csv(self):
        path=filedialog.askopenfilename(title='Select metadata CSV',
            filetypes=[('CSV files','*.csv'),('All files','*.*')])
        if path: self._load_csv_path(path)

    def _load_csv_path(self,path):
        try:
            with open(path,newline='',encoding='utf-8-sig') as f:
                reader=csv.DictReader(f)
                self.csv_rows=list(reader)
                self.csv_headers=list(reader.fieldnames or [])
            self.csv_path.set(path)
            self.csv_info.configure(
                text=f'✓  {len(self.csv_rows)} rows · {len(self.csv_headers)} columns',fg=GRN)
            self.log(f'✓  CSV loaded — {len(self.csv_rows)} rows · {os.path.basename(path)}','ok')
            self.set_status(f'CSV: {len(self.csv_rows)} rows',GRN)
            add_recent(self.prefs,'recent_csv',path)
            self._refresh_csv_recent()
            self._update_combos()
            self._update_match()
        except Exception as e:
            messagebox.showerror('CSV Error',str(e))

    def _update_combos(self):
        opts=['(skip)']+self.csv_headers
        hints={'FILENAME':['filename','file','name','image'],
               'TITLE':['title'],'KEYWORDS':['keyword','tag','kw'],
               'DESCRIPTION':['desc','caption','description']}
        vmap={'FILENAME':self.col_file,'TITLE':self.col_title,
              'KEYWORDS':self.col_kw,'DESCRIPTION':self.col_desc}
        for label,cb in self.col_combos.items():
            cb['values']=opts
            g=next((c for h in hints.get(label,[])
                for c in self.csv_headers if h in c.lower()),'')
            vmap[label].set(g or '(skip)')

    def browse_folder(self):
        path=filedialog.askdirectory(title='Select image folder')
        if path: self._set_folder(path)

    def _set_folder(self,path):
        self.folder_path.set(path)
        self.last_folder=path
        add_recent(self.prefs,'recent_folders',path)
        self._refresh_folder_recent()
        self._update_match()
        self.log(f'✓  Folder set — {path}','ok')
        self.set_status('Folder loaded',GRN)

    def _update_match(self):
        folder=self.folder_path.get()
        col_f=self.col_file.get()
        if not folder or not self.csv_rows or not col_f or col_f=='(skip)':
            self.match_badge.configure(text=''); return
        matched=sum(1 for row in self.csv_rows
            if find_file_any_ext(folder,(row.get(col_f) or '').strip()))
        total=len(self.csv_rows)
        color=GRN if matched==total else AMB if matched>0 else RED
        self.match_badge.configure(
            text=f'  ✓ {matched} of {total} files matched',fg=color)

    def open_folder(self):
        f=self.last_folder or self.folder_path.get()
        if f and os.path.exists(f):
            os.startfile(f)

    def reset_all(self):
        if self.running:
            messagebox.showwarning('Busy','Wait for current job to finish.'); return
        if not messagebox.askyesno('Reset','Clear everything and start fresh?'): return
        for v in [self.csv_path,self.folder_path,self.col_file,
                  self.col_title,self.col_kw,self.col_desc]:
            v.set('')
        self.csv_headers=[]; self.csv_rows=[]
        self.csv_info.configure(text='')
        self.match_badge.configure(text='')
        for cb in self.col_combos.values(): cb['values']=[]
        self.sb_prog.configure(value=0)
        self.p_ok.configure(text='0 embedded')
        self.p_warn.configure(text='0 not found')
        self.p_err.configure(text='0 errors')
        self.embed_btn.configure(state='normal',text='▶   Embed Metadata Now')
        self.open_folder_btn.pack_forget()
        self.clear_log()
        self.log('↺  Reset — ready for new batch','info')
        self.set_status(f'Ready{" — Last: "+self.last_summary if self.last_summary else ""}',TEXT3)

    def export_log(self):
        content=self.log_text.get('1.0','end').strip()
        if not content:
            messagebox.showinfo('Export Log','Log is empty.'); return
        path=filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text files','*.txt')],
            initialfile=f'embed_log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        if path:
            with open(path,'w',encoding='utf-8') as f: f.write(content)
            self.log(f'✓  Log saved → {os.path.basename(path)}','ok')

    def start_embed(self):
        if self.running: return
        et=find_exiftool()
        if not et:
            messagebox.showerror('ExifTool not found',
                'Place exiftool.exe next to this app.\nhttps://exiftool.org'); return
        if not self.csv_rows:
            messagebox.showerror('No CSV','Load a CSV first.'); return
        if not self.folder_path.get():
            messagebox.showerror('No folder','Select the image folder.'); return
        fc=self.col_file.get()
        if not fc or fc=='(skip)':
            messagebox.showerror('Column missing','Select the filename column.'); return
        self.running=True
        self.embed_btn.configure(state='disabled',text='Processing…')
        threading.Thread(target=self.run_embed,args=(et,),daemon=True).start()

    def run_embed(self,et):
        folder=self.folder_path.get()
        col_f=self.col_file.get(); col_t=self.col_title.get()
        col_k=self.col_kw.get(); col_d=self.col_desc.get()
        total=len(self.csv_rows); ok=skipped=errors=0
        self.root.after(0,lambda: self.sb_prog.configure(maximum=total,value=0))
        self.root.after(0,lambda: self.log(f'▶  Batch started — {total} rows','info'))

        for i,row in enumerate(self.csv_rows):
            filename=(row.get(col_f) or '').strip()
            if not filename:
                skipped+=1
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue
            filepath=find_file_any_ext(folder,filename)
            if not filepath:
                skipped+=1
                self.root.after(0,lambda fn=filename: self.log(f'⚠  Not found: {fn}','warn'))
                self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                    self._prog(n,t,o,s,e)); continue
            cmd=[et,'-overwrite_original','-codedcharacterset=UTF8']
            title=(row.get(col_t) or '').strip() if col_t and col_t!='(skip)' else ''
            kw_raw=(row.get(col_k) or '').strip() if col_k and col_k!='(skip)' else ''
            desc=(row.get(col_d) or '').strip() if col_d and col_d!='(skip)' else ''
            if title: cmd+=[f'-Title={title}',f'-ObjectName={title}',f'-Headline={title}']
            if kw_raw:
                for kw in [k.strip() for k in kw_raw.replace(';',',').split(',') if k.strip()]:
                    cmd+=[f'-Keywords={kw}',f'-Subject={kw}']
            if desc: cmd+=[f'-Description={desc}',f'-Caption-Abstract={desc}']
            cmd.append(filepath)
            try:
                flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                res=subprocess.run(cmd,capture_output=True,text=True,timeout=30,creationflags=flags)
                actual=os.path.basename(filepath)
                if res.returncode==0:
                    ok+=1
                    self.root.after(0,lambda fn=actual: self.log(f'✓  {fn}','ok'))
                else:
                    errors+=1
                    err=(res.stderr or res.stdout or 'Unknown').strip()
                    self.root.after(0,lambda fn=actual,e=err: self.log(f'✗  {fn} — {e}','err'))
            except Exception as ex:
                errors+=1
                self.root.after(0,lambda fn=filename,e=str(ex): self.log(f'✗  {fn} — {e}','err'))
            self.root.after(0,lambda n=i+1,t=total,o=ok,s=skipped,e=errors:
                self._prog(n,t,o,s,e))

        summary=f'{ok} embedded · {skipped} not found · {errors} errors'
        self.last_summary=summary
        self.root.after(0,lambda: (
            self.log(f'● Done — {summary}','info'),
            self.set_status(f'Done — {summary}',GRN),
            self.embed_btn.configure(state='normal',text='▶   Embed Metadata Now'),
            self.open_folder_btn.pack(fill='x',pady=(6,0)),
            setattr(self,'running',False)
        ))

    def _prog(self,n,total,ok,skipped,errors):
        self.sb_prog.configure(value=n)
        self.set_status(f'Processing {n} of {total}…',BLU)
        self.p_ok.configure(text=f'{ok} embedded')
        self.p_warn.configure(text=f'{skipped} not found')
        self.p_err.configure(text=f'{errors} errors')

if __name__=='__main__':
    root=tk.Tk()
    App(root)
    root.mainloop()
