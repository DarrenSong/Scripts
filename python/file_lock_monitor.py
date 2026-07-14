import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import os
import subprocess
import threading


class FileLockMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("文件占用监控")
        self.root.geometry("900x560")
        self.root.minsize(700, 400)

        self.setup_ui()
        self.refresh()

    # ── UI ──────────────────────────────────────────────
    def setup_ui(self):
        # 顶部工具栏
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=6, pady=(6, 0))

        self.refresh_btn = tk.Button(toolbar, text="刷新", width=8, command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT)

        self.auto_var = tk.BooleanVar(value=False)
        self.auto_btn = tk.Checkbutton(toolbar, text="自动刷新(5s)", variable=self.auto_var,
                                       command=self.toggle_auto)
        self.auto_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT)

        # 搜索框
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=6, pady=(4, 0))
        tk.Label(search_frame, text="过滤:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_filter)
        tk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # 表格
        cols = ("filename", "filepath", "process", "pid")
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("filename", text="文件名")
        self.tree.heading("filepath", text="文件路径")
        self.tree.heading("process", text="占用进程")
        self.tree.heading("pid", text="PID")

        self.tree.column("filename", width=180, minwidth=100)
        self.tree.column("filepath", width=360, minwidth=150)
        self.tree.column("process", width=160, minwidth=80)
        self.tree.column("pid", width=70, minwidth=50)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # 右键菜单
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="打开文件所在目录", command=self.open_file_location)
        self.ctx_menu.add_command(label="复制文件路径", command=self.copy_filepath)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="强制结束进程", command=self.kill_process)

        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<Double-1>", self.on_double_click)

        # 所有数据（未过滤）
        self.all_items = []  # [(filename, filepath, process, pid), ...]

    # ── 数据采集 ────────────────────────────────────────
    def refresh(self):
        self.refresh_btn.config(state=tk.DISABLED)
        self.status_var.set("正在扫描进程...")
        self.root.update_idletasks()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        results = []
        seen = set()
        procs = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                procs.append((p, p.info['name'], p.info['pid']))
            except Exception:
                pass

        total = len(procs)
        for idx, (proc, name, pid) in enumerate(procs):
            try:
                files = proc.open_files()
                for f in files:
                    path = f.path
                    key = (path, pid)
                    if key not in seen:
                        seen.add(key)
                        fname = os.path.basename(path)
                        results.append((fname, path, name or "", pid))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            except Exception:
                pass
            # 每 50 个进程回调一次进度
            if idx % 50 == 0:
                self.root.after(0, lambda i=idx, t=total: self.status_var.set(f"正在扫描... {i}/{t}"))

        self.root.after(0, self._on_scan_done, results)

    def _on_scan_done(self, results):
        self.all_items = results
        self._apply_filter()
        self.refresh_btn.config(state=tk.NORMAL)
        self.status_var.set(f"共 {len(results)} 条占用记录")

    # ── 过滤 ────────────────────────────────────────────
    def on_filter(self, *_):
        self._apply_filter()

    def _apply_filter(self):
        keyword = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for fname, fpath, proc, pid in self.all_items:
            if keyword and keyword not in fname.lower() and keyword not in fpath.lower() and keyword not in proc.lower():
                continue
            self.tree.insert("", tk.END, values=(fname, fpath, proc, pid))

    # ── 自动刷新 ────────────────────────────────────────
    def toggle_auto(self):
        if self.auto_var.get():
            self._auto_refresh()

    def _auto_refresh(self):
        if not self.auto_var.get():
            return
        self.refresh()
        self.root.after(5000, self._auto_refresh)

    # ── 右键菜单 ────────────────────────────────────────
    def on_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.ctx_menu.post(event.x_root, event.y_root)

    def on_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.open_file_location()

    # ── 右键操作 ────────────────────────────────────────
    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], 'values')
        return {"filename": vals[0], "filepath": vals[1], "process": vals[2], "pid": int(vals[3])}

    def open_file_location(self):
        info = self._get_selected()
        if not info:
            return
        fpath = info["filepath"]
        if os.path.exists(fpath):
            subprocess.Popen(['explorer', '/select,', fpath])
        else:
            dirpath = os.path.dirname(fpath)
            if os.path.exists(dirpath):
                subprocess.Popen(['explorer', dirpath])
            else:
                messagebox.showwarning("提示", f"路径不存在:\n{fpath}")

    def copy_filepath(self):
        info = self._get_selected()
        if not info:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(info["filepath"])
        self.status_var.set("已复制路径到剪贴板")

    def kill_process(self):
        info = self._get_selected()
        if not info:
            return
        pid = info["pid"]
        name = info["process"]
        if not messagebox.askyesno("确认", f"确定要强制结束进程 \"{name}\" (PID: {pid}) 吗？\n\n"
                                            "注意：强制结束进程可能导致数据丢失。"):
            return
        try:
            p = psutil.Process(pid)
            p.kill()
            self.status_var.set(f"已终止进程 {name} (PID: {pid})")
            messagebox.showinfo("成功", f"已终止进程 {name} (PID: {pid})")
            # 刷新列表
            self.refresh()
        except psutil.NoSuchProcess:
            messagebox.showwarning("提示", f"进程已不存在 (PID: {pid})")
        except psutil.AccessDenied:
            messagebox.showerror("失败", f"权限不足，无法终止进程 {name} (PID: {pid})\n\n请尝试以管理员身份运行本程序。")
        except Exception as e:
            messagebox.showerror("错误", f"终止进程失败:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileLockMonitor(root)
    root.mainloop()
