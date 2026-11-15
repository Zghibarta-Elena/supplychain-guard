"""Native desktop interface for SupplyGuard (Tkinter)."""
import csv
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parent.parent

# label, argument, picker: directory / open / save / text / choice
TASKS = {
    'Experimente capitolele 4 și 5': ('experiment', 'Rulează E1 (Express/Flask, Syft) și E2 (Cosign T0–T6). Necesită Python 3.11+, npm și pregătirea inițială: python3 -m supplyguard experiment --prepare. Poate dura câteva minute.', []),
    'Verificare SBOM': ('check', 'Verifică inventarul de componente conform politicii organizației.', [
        ('SBOM CycloneDX', 'sbom', 'open'), ('Politică JSON', '--policy', 'open')]),
    'Generare SBOM': ('sbom', 'Generează un inventar CycloneDX pentru un director folosind Syft.', [
        ('Director aplicație', 'source', 'directory'), ('Salvează SBOM', '--output', 'save')]),
    'Inventar aprobat': ('snapshot', 'Salvează hash-urile fișierelor aprobate. Alege o destinație în afara directorului scanat.', [
        ('Director aplicație', 'directory', 'directory'), ('Salvează inventarul', '--output', 'save')]),
    'Comparare integritate': ('compare', 'Identifică fișiere adăugate, eliminate sau modificate față de inventarul aprobat.', [
        ('Director aplicație', 'directory', 'directory'), ('Inventar aprobat', '--baseline', 'open')]),
    'Semnare artefact': ('sign', 'Semnează cu Cosign. Se deschide autentificarea în browser; datele semnării sunt publicate în jurnalul Sigstore.', [
        ('Artefact', 'artifact', 'open'), ('Salvează bundle', '--bundle', 'save')]),
    'Verificare semnătură': ('verify', 'Verifică integritatea și identitatea exactă a semnatarului aprobat.', [
        ('Artefact', 'artifact', 'open'), ('Bundle Sigstore', '--bundle', 'open'),
        ('Identitate aprobată', '--identity', 'text'), ('Issuer OIDC', '--issuer', 'text')]),
    'Laborator atacuri': ('simulate', 'Demonstrații cu fișiere text temporare. Nu execută malware și nu reproduc exploatarea reală.', [
        ('Scenariu', 'scenario', 'choice')]),
}


def build_command(task, values):
    """Build argv without invoking a shell; keep spaces and metacharacters literal."""
    command, _, fields = TASKS[task]
    argv = [sys.executable, '-u', '-m', 'supplyguard', command]
    for label, argument, kind in fields:
        value = values.get(argument, '').strip()
        if not value:
            raise ValueError(f'Completează câmpul: {label}')
        if kind == 'directory' and not Path(value).is_dir():
            raise ValueError(f'Director inexistent: {value}')
        if kind == 'open' and not Path(value).is_file():
            raise ValueError(f'Fișier inexistent: {value}')
        if kind == 'save' and not Path(value).parent.is_dir():
            raise ValueError(f'Directorul destinației nu există: {value}')
        if argument.startswith('--'):
            argv.append(argument)
        argv.append('dir:' + value if command == 'sbom' and argument == 'source' else value)
    return argv


def result_rows(output, code):
    """Convert structured CLI output to rows without losing nested findings."""
    rows = [('Rezultat', 'Finalizat' if code == 0 else 'Constatări' if code == 1 else 'Eroare'),
            ('Cod ieșire', str(code))]
    def visit(key, value):
        if isinstance(value, dict):
            for child, item in value.items():
                visit(f'{key}.{child}' if key else child, item)
        elif isinstance(value, list):
            if not value:
                rows.append((key, '—'))
            for index, item in enumerate(value, 1):
                visit(f'{key}[{index}]', item)
        else:
            rows.append((key, ('Da' if value else 'Nu') if isinstance(value, bool) else str(value)))
    try:
        visit('', json.loads(output))
    except (ValueError, TypeError):
        for line in output.splitlines():
            if line.strip():
                rows.append(('Mesaj', line))
    return rows


def main():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        from tkinter import font as tkfont
        from tkinter.scrolledtext import ScrolledText
    except ImportError:
        print('Tkinter lipsește. Ubuntu/Debian: sudo apt install python3-tk. Windows: instalează Python cu Tcl/Tk.', file=sys.stderr)
        return 2

    class App:
        def __init__(self, root):
            self.root = root
            self.process = None
            self.busy = False
            self.events = queue.Queue()
            self.values = {}
            self.saved = {}
            root.title('SupplyGuard · Release Security')
            root.geometry('1120x820')
            root.minsize(880, 740)
            root.configure(bg='#f3f5f8')
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('.', font=('Segoe UI', 11))
            style.configure('TFrame', background='#f3f5f8')
            style.configure('TLabel', background='#f3f5f8', foreground='#243047')
            style.configure('Title.TLabel', font=('Segoe UI', 25, 'bold'))
            style.configure('TButton', padding=(12, 8))
            style.configure('Treeview', rowheight=32)
            style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'))
            style.configure('Accent.TButton', background='#175cbd', foreground='white')
            style.map('Accent.TButton', background=[('active', '#124b9c'), ('disabled', '#a0aec0')])
            outer = ttk.Frame(root, padding=24)
            outer.pack(fill='both', expand=True)
            ttk.Label(outer, text='SupplyGuard', style='Title.TLabel').pack(anchor='w')
            ttk.Label(outer, text='Controlul integrității și al componentelor pentru fiecare release').pack(anchor='w', pady=(4, 12))
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
            self.env = env
            tools = '   •   '.join(f'{tool}: {"disponibil" if shutil.which(tool, path=env["PATH"]) else "lipsește"}' for tool in ('syft', 'cosign'))
            ttk.Label(outer, text=tools).pack(anchor='w', pady=(0, 16))
            ttk.Label(outer, text='OPERAȚIUNE').pack(anchor='w')
            self.task = tk.StringVar(value='Verificare SBOM')
            self.selector = ttk.Combobox(outer, textvariable=self.task, values=list(TASKS), state='readonly')
            self.selector.pack(fill='x', pady=(6, 12))
            self.selector.bind('<<ComboboxSelected>>', self.render)
            self.description = ttk.Label(outer, wraplength=980)
            self.description.pack(anchor='w', pady=(0, 12))
            self.form = ttk.Frame(outer)
            self.form.pack(fill='x')
            controls = ttk.Frame(outer)
            controls.pack(fill='x', pady=16)
            self.run_button = ttk.Button(controls, text='Rulează verificarea', style='Accent.TButton', command=self.run)
            self.run_button.pack(side='left')
            self.status = ttk.Label(controls, text='Pregătit')
            self.status.pack(side='left', padx=16)
            ttk.Button(controls, text='Exportă rezultatul', command=self.export).pack(side='right')
            ttk.Button(controls, text='Tabele E1/E2', command=self.show_experiments).pack(side='right', padx=8)
            self.progress = ttk.Progressbar(outer, mode='indeterminate')
            self.progress.pack(fill='x', pady=(0, 12))
            ttk.Label(outer, text='REZULTATE').pack(anchor='w', pady=(0, 6))
            tabs = ttk.Notebook(outer)
            tabs.pack(fill='both', expand=True)
            table_frame = ttk.Frame(tabs)
            log_frame = ttk.Frame(tabs)
            tabs.add(table_frame, text='Tabel')
            tabs.add(log_frame, text='Jurnal')
            self.table = ttk.Treeview(table_frame, columns=('field', 'value'), show='headings')
            self.table.heading('field', text='Indicator / element')
            self.table.heading('value', text='Rezultat / detalii')
            self.table.column('field', width=240)
            self.table.column('value', width=700)
            scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
            scrollbar.pack(side='right', fill='y')
            horizontal = ttk.Scrollbar(table_frame, orient='horizontal', command=self.table.xview)
            horizontal.pack(side='bottom', fill='x')
            self.table.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
            self.table.pack(fill='both', expand=True)
            self.result_output = ''
            self.output = ScrolledText(log_frame, height=10, font=('Consolas', 11), bg='#111c30', fg='#e3ecf9',
                                       insertbackground='white', relief='flat', padx=14, pady=14, wrap='word')
            self.output.pack(fill='both', expand=True)
            self.output.configure(state='disabled')
            ttk.Label(outer, text='O semnătură validă confirmă originea și integritatea, nu absența codului malițios.', wraplength=980).pack(anchor='w', pady=(12, 0))
            self.render()
            root.protocol('WM_DELETE_WINDOW', self.close)
            root.after(100, self.poll)

        def render(self, event=None):
            for key, variable in self.values.items():
                self.saved[(getattr(self, 'current', ''), key)] = variable.get()
            self.current = self.task.get()
            for child in self.form.winfo_children():
                child.destroy()
            self.values = {}
            self.description.configure(text=TASKS[self.current][1])
            self.form.columnconfigure(0, weight=1)
            for index, (label, argument, kind) in enumerate(TASKS[self.current][2]):
                ttk.Label(self.form, text=label).grid(row=index * 2, column=0, sticky='w', pady=(4, 3))
                default = str(ROOT / 'policy.json') if argument == '--policy' else 'solarwinds' if kind == 'choice' else ''
                value = tk.StringVar(value=self.saved.get((self.current, argument), default))
                self.values[argument] = value
                if kind == 'choice':
                    entry = ttk.Combobox(self.form, textvariable=value, values=['solarwinds', 'xz'], state='readonly')
                else:
                    entry = ttk.Entry(self.form, textvariable=value)
                entry.grid(row=index * 2 + 1, column=0, sticky='ew', pady=(0, 3))
                if kind in ('directory', 'open', 'save'):
                    ttk.Button(self.form, text='Alege…', command=lambda v=value, k=kind: self.browse(v, k)).grid(row=index * 2 + 1, column=1, padx=(8, 0))
            self.run_button.configure(text='Rulează operațiunea')

        def browse(self, variable, kind):
            if kind == 'directory':
                path = filedialog.askdirectory(parent=self.root)
            elif kind == 'save':
                path = filedialog.asksaveasfilename(parent=self.root, defaultextension='.json', filetypes=[('JSON', '*.json'), ('Toate fișierele', '*')])
            else:
                path = filedialog.askopenfilename(parent=self.root)
            if path:
                variable.set(path)

        def append(self, text):
            self.output.configure(state='normal')
            self.output.insert('end', text)
            self.output.see('end')
            self.output.configure(state='disabled')

        def run(self):
            if self.busy:
                return
            try:
                values = {k: v.get() for k, v in self.values.items()}
                argv = build_command(self.current, values)
                for _, argument, kind in TASKS[self.current][2]:
                    if kind == 'save':
                        output = Path(values[argument]).resolve()
                        inputs = [Path(values[a]).resolve() for _, a, k in TASKS[self.current][2] if k in ('open', 'directory')]
                        if any(output == source or (source.is_dir() and source in output.parents) for source in inputs):
                            raise ValueError('Destinația trebuie să fie separată de fișierele și directorul de intrare.')
                        if output.exists() and not messagebox.askyesno('Suprascriere', f'Înlocuiești fișierul existent?\n{output}', parent=self.root):
                            return
            except ValueError as error:
                messagebox.showerror('Verifică datele', str(error), parent=self.root)
                return
            self.result_output = ''
            self.table.delete(*self.table.get_children())
            self.busy = True
            self.run_button.configure(state='disabled')
            self.selector.configure(state='disabled')
            self.status.configure(text='În curs…')
            self.progress.start(12)
            self.append(f'\n── {self.current} ──\n')
            threading.Thread(target=self.worker, args=(argv,), daemon=True).start()

        def worker(self, argv):
            try:
                self.process = subprocess.Popen(argv, cwd=ROOT, env=self.env, stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                                text=True, encoding='utf-8', errors='replace')
                for line in self.process.stdout:
                    self.events.put(('output', line))
                code = self.process.wait()
            except OSError as error:
                self.events.put(('output', f'Eroare: {error}\n'))
                code = 2
            self.events.put(('done', code))

        def poll(self):
            try:
                while True:
                    kind, value = self.events.get_nowait()
                    if kind == 'output':
                        self.result_output += value
                        self.append(value)
                    else:
                        for row in result_rows(self.result_output, value):
                            self.table.insert('', 'end', values=row)
                        self.busy = False
                        self.process = None
                        self.progress.stop()
                        self.run_button.configure(state='normal')
                        self.selector.configure(state='readonly')
                        label = 'Finalizat' if value == 0 else 'Constatări — necesită analiză' if value == 1 else 'Eroare — consultă jurnalul'
                        self.status.configure(text=label)
                        self.append(f'\n{label} (cod {value})\n')
                        if value == 0 and self.current == 'Experimente capitolele 4 și 5':
                            self.show_experiments()
            except queue.Empty:
                pass
            self.root.after(100, self.poll)

        def show_experiments(self):
            try:
                data = json.loads((ROOT / 'build/experiments/measurements.json').read_text())
            except (OSError, ValueError) as error:
                messagebox.showerror('Rezultate indisponibile', f'Rulează mai întâi experimentele E1/E2.\n{error}', parent=self.root)
                return
            window = tk.Toplevel(self.root)
            window.title('Rezultate — capitolele 4 și 5')
            window.geometry(f'{min(1800, self.root.winfo_screenwidth() - 80)}x560')
            ttk.Label(window, text='Rezultate măsurate · Express 5.1.0 / Flask 3.1.1 / Cosign T0–T6',
                      padding=12).pack(anchor='w')
            notebook = ttk.Notebook(window)
            notebook.pack(fill='both', expand=True)
            tables = [
                ('Express · 4.1', 'express', ['Cfg.', 'Moment', 'Syft', 'Componente npm', 'Acoperire producție', 'Acoperire totală', 'Componente străine', 'PURL', 'Hash', 'Licență']),
                ('Flask · 4.2', 'flask', ['Cfg.', 'Moment', 'Syft', 'Componente PyPI', 'Sursă', 'Versiuni corecte', 'PURL', 'Hash', 'Licență']),
                ('Hash-uri · 4.5', 'hashes', ['Cfg.', 'Componente npm', 'Completate', 'Cu hash']),
                ('Cosign · 5.1', 'scenarios', ['Scenariu', 'Modificare', 'Cheie', 'Rezultat', 'Cod', 'Conform așteptării'])]
            for title, key, headers in tables:
                frame = ttk.Frame(notebook)
                notebook.add(frame, text=title)
                columns = [str(i) for i in range(len(headers))]
                tree = ttk.Treeview(frame, columns=columns, show='headings')
                font = tkfont.Font(family='Segoe UI', size=11)
                for index, (column, header) in enumerate(zip(columns, headers)):
                    tree.heading(column, text=header)
                    width = max(font.measure(str(row[index])) for row in [headers, *data[key]]) + 30
                    tree.column(column, width=min(750, max(65, width)), minwidth=50, stretch=False)
                vertical = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
                vertical.pack(side='right', fill='y')
                horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
                horizontal.pack(side='bottom', fill='x')
                tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
                tree.pack(fill='both', expand=True)
                for row in data[key]:
                    tree.insert('', 'end', values=row)

        def export(self):
            path = filedialog.asksaveasfilename(parent=self.root, defaultextension='.csv', filetypes=[('Tabel CSV', '*.csv'), ('Jurnal text', '*.txt')])
            if path:
                try:
                    if Path(path).suffix.lower() == '.txt':
                        Path(path).write_text(self.output.get('1.0', 'end-1c'), encoding='utf-8')
                    else:
                        with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
                            writer = csv.writer(stream)
                            writer.writerow(['Indicator / element', 'Rezultat / detalii'])
                            writer.writerows(self.table.item(item, 'values') for item in self.table.get_children())
                except OSError as error:
                    messagebox.showerror('Export eșuat', str(error), parent=self.root)

        def close(self):
            if self.busy:
                messagebox.showinfo('Operațiune în curs', 'Așteaptă finalizarea operațiunii înainte de închidere.', parent=self.root)
                return
            self.root.destroy()

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f'Interfața necesită o sesiune desktop: {error}', file=sys.stderr)
        return 2
    App(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
