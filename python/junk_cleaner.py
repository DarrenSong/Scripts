#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统垃圾清理工具
类似于360垃圾清理，扫描并清理系统临时文件、缓存等
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
import threading
import time
from pathlib import Path
import psutil
import winreg


class JunkCleaner:
    """系统垃圾清理工具"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("系统垃圾清理工具")
        self.root.geometry("800x650")
        self.root.configure(bg="#f5f5f5")
        
        # 扫描结果
        self.scan_results = {}
        self.is_scanning = False
        self.is_cleaning = False
        self.failed_files = []  # 删除失败的文件列表
        
        # 定义扫描类别
        self.scan_categories = self._define_categories()
        
        self.setup_ui()
        
    def _define_categories(self):
        """定义扫描类别和路径"""
        user_home = Path.home()
        temp_dir = os.environ.get('TEMP', '')
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        local_appdata = os.environ.get('LOCALAPPDATA', '')
        
        categories = {
            'system_temp': {
                'name': '系统临时文件',
                'icon': '📁',
                'description': 'Windows临时文件夹中的文件',
                'paths': [
                    temp_dir,
                    os.path.join(win_dir, 'Temp'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'chrome_cache': {
                'name': 'Chrome 浏览器缓存',
                'icon': '🌐',
                'description': 'Google Chrome 浏览器缓存文件',
                'paths': [
                    os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
                    os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Code Cache'),
                    os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'ShaderCache'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'edge_cache': {
                'name': 'Edge 浏览器缓存',
                'icon': '🌐',
                'description': 'Microsoft Edge 浏览器缓存文件',
                'paths': [
                    os.path.join(local_appdata, 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
                    os.path.join(local_appdata, 'Microsoft', 'Edge', 'User Data', 'Default', 'Code Cache'),
                    os.path.join(local_appdata, 'Microsoft', 'Edge', 'User Data', 'ShaderCache'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'firefox_cache': {
                'name': 'Firefox 浏览器缓存',
                'icon': '🌐',
                'description': 'Mozilla Firefox 浏览器缓存文件',
                'paths': [
                    os.path.join(local_appdata, 'Mozilla', 'Firefox', 'Profiles'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'windows_update': {
                'name': 'Windows更新缓存',
                'icon': '🔄',
                'description': 'Windows Update下载的更新文件',
                'paths': [
                    os.path.join(win_dir, 'SoftwareDistribution', 'Download'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'prefetch': {
                'name': '预读取文件',
                'icon': '⚡',
                'description': 'Windows Prefetch预读取文件',
                'paths': [
                    os.path.join(win_dir, 'Prefetch'),
                ],
                'patterns': ['*.pf'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'thumbnails': {
                'name': '缩略图缓存',
                'icon': '🖼️',
                'description': 'Windows缩略图缓存文件',
                'paths': [
                    os.path.join(local_appdata, 'Microsoft', 'Windows', 'Explorer'),
                ],
                'patterns': ['thumbcache_*.db'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'error_reports': {
                'name': '错误报告',
                'icon': '🐛',
                'description': 'Windows错误报告和崩溃转储',
                'paths': [
                    os.path.join(local_appdata, 'Microsoft', 'Windows', 'WER'),
                    os.path.join(local_appdata, 'CrashDumps'),
                    os.path.join(win_dir, 'Logs', 'CBS'),
                ],
                'patterns': ['*.*'],
                'checked': tk.BooleanVar(value=True),
                'size': 0,
                'count': 0,
                'files': []
            },
            'recent_docs': {
                'name': '最近文档',
                'icon': '📄',
                'description': '最近访问的文档快捷方式',
                'paths': [
                    os.path.join(user_home, 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Recent'),
                ],
                'patterns': ['*.lnk'],
                'checked': tk.BooleanVar(value=False),
                'size': 0,
                'count': 0,
                'files': []
            },
            'recycle_bin': {
                'name': '回收站',
                'icon': '🗑️',
                'description': '回收站中的文件',
                'paths': [],  # 特殊处理
                'patterns': [],
                'checked': tk.BooleanVar(value=False),
                'size': 0,
                'count': 0,
                'files': []
            }
        }
        return categories
    
    def setup_ui(self):
        """创建界面"""
        # 标题区域
        title_frame = tk.Frame(self.root, bg="#2196F3", height=80)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🧹 系统垃圾清理工具",
            font=("Microsoft YaHei", 20, "bold"),
            fg="white",
            bg="#2196F3"
        )
        title_label.pack(pady=20)
        
        # 主内容区域
        main_frame = tk.Frame(self.root, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 扫描类别列表
        list_frame = tk.LabelFrame(
            main_frame,
            text="扫描项目",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#f5f5f5",
            padx=10,
            pady=10
        )
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建可滚动的类别列表
        canvas = tk.Canvas(list_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加类别复选框
        self.category_widgets = {}
        for key, category in self.scan_categories.items():
            frame = tk.Frame(self.scrollable_frame, bg="#f5f5f5")
            frame.pack(fill=tk.X, pady=2)
            
            cb = tk.Checkbutton(
                frame,
                variable=category['checked'],
                bg="#f5f5f5",
                activebackground="#f5f5f5"
            )
            cb.pack(side=tk.LEFT)
            
            icon_label = tk.Label(
                frame,
                text=category['icon'],
                font=("Segoe UI Emoji", 16),
                bg="#f5f5f5"
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
            
            text_frame = tk.Frame(frame, bg="#f5f5f5")
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            name_label = tk.Label(
                text_frame,
                text=category['name'],
                font=("Microsoft YaHei", 10, "bold"),
                bg="#f5f5f5",
                anchor="w"
            )
            name_label.pack(anchor="w")
            
            desc_label = tk.Label(
                text_frame,
                text=category['description'],
                font=("Microsoft YaHei", 8),
                fg="#666",
                bg="#f5f5f5",
                anchor="w"
            )
            desc_label.pack(anchor="w")
            
            size_label = tk.Label(
                frame,
                text="待扫描",
                font=("Consolas", 10),
                fg="#999",
                bg="#f5f5f5"
            )
            size_label.pack(side=tk.RIGHT, padx=10)
            
            self.category_widgets[key] = {
                'size_label': size_label,
                'frame': frame
            }
        
        # 进度区域
        progress_frame = tk.Frame(main_frame, bg="#f5f5f5")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = tk.Label(
            progress_frame,
            text="点击\"扫描垃圾\"开始扫描",
            font=("Microsoft YaHei", 9),
            fg="#666",
            bg="#f5f5f5"
        )
        self.status_label.pack(anchor="w")
        
        # 总计显示
        self.total_label = tk.Label(
            progress_frame,
            text="可清理: 0 MB  |  文件数: 0",
            font=("Microsoft YaHei", 11, "bold"),
            fg="#2196F3",
            bg="#f5f5f5"
        )
        self.total_label.pack(anchor="w", pady=(5, 0))
        
        # 按钮区域
        self.button_frame = tk.Frame(main_frame, bg="#f5f5f5")
        self.button_frame.pack(fill=tk.X)
        
        self.scan_btn = tk.Button(
            self.button_frame,
            text="🔍 扫描垃圾",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#2196F3",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=15,
            height=2,
            command=self.start_scan
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.clean_btn = tk.Button(
            self.button_frame,
            text="🧹 立即清理",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=15,
            height=2,
            command=self.start_clean,
            state=tk.DISABLED
        )
        self.clean_btn.pack(side=tk.LEFT, padx=5)
        
        exit_btn = tk.Button(
            self.button_frame,
            text="退出",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#9E9E9E",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=10,
            height=2,
            command=self.root.quit
        )
        exit_btn.pack(side=tk.RIGHT, padx=5)
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / 1024 / 1024:.1f} MB"
        else:
            return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"
    
    def scan_category(self, key, category):
        """扫描单个类别"""
        files = []
        total_size = 0
        
        # 特殊处理回收站
        if key == 'recycle_bin':
            try:
                # 使用 PowerShell 获取回收站大小
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', 
                     '(New-Object -ComObject Shell.Application).NameSpace(0xa).Items() | ' +
                     'Measure-Object -Property Size -Sum | Select-Object -ExpandProperty Sum'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    size = int(result.stdout.strip())
                    total_size = size
                    files.append('RECYCLE_BIN')
            except Exception:
                pass
            return total_size, len(files), files
        
        # 扫描普通路径
        for path in category['paths']:
            if not os.path.exists(path):
                continue
            
            try:
                if os.path.isfile(path):
                    # 单文件
                    try:
                        size = os.path.getsize(path)
                        files.append(path)
                        total_size += size
                    except Exception:
                        pass
                else:
                    # 目录
                    for root_dir, dirs, filenames in os.walk(path):
                        for filename in filenames:
                            try:
                                file_path = os.path.join(root_dir, filename)
                                
                                # 检查是否匹配模式
                                match = False
                                for pattern in category['patterns']:
                                    if pattern == '*.*':
                                        match = True
                                        break
                                    elif filename.endswith(pattern.replace('*', '')):
                                        match = True
                                        break
                                
                                if match:
                                    size = os.path.getsize(file_path)
                                    files.append(file_path)
                                    total_size += size
                            except Exception:
                                pass
            except Exception:
                pass
        
        return total_size, len(files), files
    
    def start_scan(self):
        """开始扫描"""
        if self.is_scanning:
            return
        
        self.is_scanning = True
        self.scan_btn.config(state=tk.DISABLED, text="扫描中...")
        self.clean_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # 重置结果
        for key in self.scan_categories:
            self.scan_categories[key]['size'] = 0
            self.scan_categories[key]['count'] = 0
            self.scan_categories[key]['files'] = []
        
        # 启动扫描线程
        thread = threading.Thread(target=self.scan_worker, daemon=True)
        thread.start()
    
    def scan_worker(self):
        """扫描工作线程"""
        categories_to_scan = [
            (key, cat) for key, cat in self.scan_categories.items()
            if cat['checked'].get()
        ]
        
        total = len(categories_to_scan)
        
        for idx, (key, category) in enumerate(categories_to_scan):
            self.root.after(0, self.update_status, f"正在扫描: {category['name']}...")
            
            size, count, files = self.scan_category(key, category)
            
            self.scan_categories[key]['size'] = size
            self.scan_categories[key]['count'] = count
            self.scan_categories[key]['files'] = files
            
            # 更新UI
            self.root.after(0, self.update_category_display, key)
            
            # 更新进度
            progress = (idx + 1) / total * 100
            self.root.after(0, self.progress_var.set, progress)
        
        # 扫描完成
        self.root.after(0, self.scan_complete)
    
    def update_status(self, text):
        """更新状态文本"""
        self.status_label.config(text=text)
    
    def update_category_display(self, key):
        """更新类别显示"""
        category = self.scan_categories[key]
        widget = self.category_widgets[key]
        
        if category['size'] > 0:
            size_text = self.format_size(category['size'])
            widget['size_label'].config(text=size_text, fg="#F44336")
        else:
            widget['size_label'].config(text="0 B", fg="#4CAF50")
        
        # 更新总计
        total_size = sum(cat['size'] for cat in self.scan_categories.values())
        total_count = sum(cat['count'] for cat in self.scan_categories.values())
        self.total_label.config(
            text=f"可清理: {self.format_size(total_size)}  |  文件数: {total_count}"
        )
    
    def scan_complete(self):
        """扫描完成"""
        self.is_scanning = False
        self.scan_btn.config(state=tk.NORMAL, text="🔍 重新扫描")
        self.status_label.config(text="扫描完成！")
        
        # 启用清理按钮
        total_size = sum(cat['size'] for cat in self.scan_categories.values())
        if total_size > 0:
            self.clean_btn.config(state=tk.NORMAL)
        else:
            self.clean_btn.config(state=tk.DISABLED)
            self.status_label.config(text="扫描完成！没有发现可清理的垃圾文件。")
    
    def start_clean(self):
        """开始清理"""
        if self.is_cleaning or self.is_scanning:
            return
        
        # 确认对话框
        total_size = sum(cat['size'] for cat in self.scan_categories.values())
        total_count = sum(cat['count'] for cat in self.scan_categories.values())
        
        if not messagebox.askyesno(
            "确认清理",
            f"确定要清理选中的垃圾文件吗？\n\n"
            f"可清理: {self.format_size(total_size)}\n"
            f"文件数: {total_count}\n\n"
            f"此操作不可恢复！"
        ):
            return
        
        self.is_cleaning = True
        self.clean_btn.config(state=tk.DISABLED, text="清理中...")
        self.scan_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # 启动清理线程
        thread = threading.Thread(target=self.clean_worker, daemon=True)
        thread.start()
    
    def clean_worker(self):
        """清理工作线程"""
        categories_to_clean = [
            (key, cat) for key, cat in self.scan_categories.items()
            if cat['checked'].get() and cat['size'] > 0
        ]
        
        total = len(categories_to_clean)
        cleaned_size = 0
        cleaned_count = 0
        failed_files = []
        
        for idx, (key, category) in enumerate(categories_to_clean):
            self.root.after(0, self.update_status, f"正在清理: {category['name']}...")
            
            # 特殊处理回收站
            if key == 'recycle_bin':
                try:
                    import subprocess
                    subprocess.run(
                        ['powershell', '-Command', 
                         'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
                        timeout=30
                    )
                    cleaned_size += category['size']
                    cleaned_count += category['count']
                except Exception:
                    failed_files.append('[回收站]')
            else:
                # 清理普通文件
                for file_path in category['files']:
                    try:
                        if os.path.isfile(file_path):
                            size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_size += size
                            cleaned_count += 1
                        elif os.path.isdir(file_path):
                            try:
                                shutil.rmtree(file_path)
                            except Exception:
                                failed_files.append(file_path)
                    except PermissionError:
                        failed_files.append(file_path)
                    except Exception:
                        failed_files.append(file_path)
            
            # 更新进度
            progress = (idx + 1) / total * 100
            self.root.after(0, self.progress_var.set, progress)
        
        # 清理完成
        self.root.after(0, self.clean_complete, cleaned_size, cleaned_count, failed_files)
    
    def clean_complete(self, cleaned_size, cleaned_count, failed_files):
        """清理完成"""
        self.is_cleaning = False
        self.failed_files = [f for f in failed_files if f != '[回收站]']
        failed_count = len(failed_files)
        
        self.clean_btn.config(state=tk.DISABLED, text="🧹 立即清理")
        self.scan_btn.config(state=tk.NORMAL, text="🔍 重新扫描")
        
        # 重置显示
        for key in self.scan_categories:
            self.scan_categories[key]['size'] = 0
            self.scan_categories[key]['count'] = 0
            self.scan_categories[key]['files'] = []
            self.category_widgets[key]['size_label'].config(text="已清理", fg="#4CAF50")
        
        self.total_label.config(text="清理完成！")
        self.progress_var.set(100)
        
        # 显示结果
        result_msg = f"清理完成！\n\n"
        result_msg += f"已清理: {self.format_size(cleaned_size)}\n"
        result_msg += f"文件数: {cleaned_count}"
        
        if failed_count > 0:
            result_msg += f"\n\n有 {len(self.failed_files)} 个文件因被占用无法删除\n"
            result_msg += f"点击\"查看占用\"可查看占用进程并强制删除"
            
            # 显示查看占用按钮
            self.lock_btn = tk.Button(
                self.button_frame,
                text=f"🔍 查看占用 ({len(self.failed_files)})",
                font=("Microsoft YaHei", 10, "bold"),
                bg="#FF9800",
                fg="white",
                relief="flat",
                cursor="hand2",
                width=18,
                height=2,
                command=self.show_locked_files
            )
            self.lock_btn.pack(side=tk.LEFT, padx=5)
        
        messagebox.showinfo("清理完成", result_msg)
        
        self.status_label.config(text="清理完成！点击\"扫描垃圾\"重新扫描。")
    
    def find_all_file_lockers(self, target_files, progress_callback=None):
        """一次性遍历所有进程，查找占用目标文件的进程"""
        # 构建目标文件集合（小写归一化）
        target_set = {}
        for f in target_files:
            target_set[f.lower().replace('/', '\\')] = f
        
        # 结果映射
        file_lockers = {f: [] for f in target_files}
        
        # 获取所有进程列表
        all_procs = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                all_procs.append(proc)
            except Exception:
                pass
        
        total = len(all_procs)
        
        for idx, proc in enumerate(all_procs):
            try:
                open_files = proc.open_files()
                for f in open_files:
                    f_path = f.path.lower().replace('/', '\\')
                    if f_path in target_set:
                        original_path = target_set[f_path]
                        file_lockers[original_path].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'file': f.path
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            except Exception:
                pass
            
            # 回调进度
            if progress_callback and (idx % 10 == 0 or idx == total - 1):
                progress_callback(idx + 1, total)
        
        return file_lockers
    
    def show_locked_files(self):
        """显示被占用文件的对话框（后台线程分析 + 进度条）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("被占用的文件")
        dialog.geometry("700x500")
        dialog.configure(bg="#f5f5f5")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 标题
        tk.Label(
            dialog,
            text=f"以下 {len(self.failed_files)} 个文件被其他进程占用",
            font=("Microsoft YaHei", 12, "bold"),
            bg="#f5f5f5"
        ).pack(pady=10)
        
        # 进度区域
        progress_frame = tk.Frame(dialog, bg="#f5f5f5")
        progress_frame.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_frame, variable=progress_var,
            maximum=100, mode='determinate'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        progress_label = tk.Label(
            progress_frame,
            text="正在扫描进程... 0%",
            font=("Microsoft YaHei", 9),
            fg="#666",
            bg="#f5f5f5"
        )
        progress_label.pack(anchor="w")
        
        # 文件列表区域（先隐藏，分析完再显示）
        list_frame = tk.Frame(dialog, bg="#f5f5f5")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        columns = ("file", "locker")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        tree.heading("file", text="文件路径")
        tree.heading("locker", text="占用进程")
        tree.column("file", width=400, anchor="w")
        tree.column("locker", width=250, anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮区域（先隐藏）
        btn_frame = tk.Frame(dialog, bg="#f5f5f5")
        
        # file_lockers 用于 force_delete
        file_lockers_ref = {}
        
        def on_progress(current, total):
            """后台线程回调：更新进度条"""
            pct = current / total * 100
            progress_var.set(pct)
            progress_label.config(text=f"正在扫描进程... {current}/{total} ({int(pct)}%)")
        
        def on_analysis_done(file_lockers):
            """后台线程完成：填充表格、显示按钮"""
            file_lockers_ref.update(file_lockers)
            
            # 填充表格
            for file_path in self.failed_files:
                lockers = file_lockers.get(file_path, [])
                if lockers:
                    locker_str = ", ".join(f"{l['name']}({l['pid']})" for l in lockers)
                else:
                    locker_str = "系统进程或未知占用"
                tree.insert('', 'end', values=(file_path, locker_str))
            
            # 隐藏进度，显示按钮
            progress_frame.pack_forget()
            
            btn_frame.pack(fill=tk.X, padx=15, pady=10)
            
            self.status_label.config(text="分析完成")
        
        def start_analysis():
            """在后台线程中执行分析"""
            def worker():
                lockers = self.find_all_file_lockers(self.failed_files, progress_callback=on_progress)
                self.root.after(0, on_analysis_done, lockers)
            
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
        
        def force_delete_all():
            """强制删除所有被占用文件"""
            if not messagebox.askyesno(
                "确认强制删除",
                "强制删除将终止占用这些文件的进程，然后删除文件。\n"
                "这可能导致相关程序数据丢失！\n\n确定继续？"
            ):
                return
            
            # 收集所有需要终止的进程 PID
            pids_to_kill = set()
            for file_path, lockers in file_lockers_ref.items():
                for locker in lockers:
                    pids_to_kill.add(locker['pid'])
            
            # 终止进程
            killed = 0
            for pid in pids_to_kill:
                try:
                    proc = psutil.Process(pid)
                    proc.kill()
                    killed += 1
                except Exception:
                    pass
            
            time.sleep(1)
            
            # 重试删除文件
            retry_ok = 0
            retry_fail = 0
            for file_path in self.failed_files:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        retry_ok += 1
                except Exception:
                    retry_fail += 1
            
            dialog.destroy()
            messagebox.showinfo(
                "强制删除完成",
                f"终止进程: {killed} 个\n"
                f"成功删除: {retry_ok} 个\n"
                f"仍然失败: {retry_fail} 个"
            )
            
            # 更新主界面
            self.failed_files = []
            if hasattr(self, 'lock_btn'):
                self.lock_btn.destroy()
        
        force_btn = tk.Button(
            btn_frame,
            text="⚠️ 强制终止进程并删除",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#F44336",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=force_delete_all
        )
        force_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = tk.Button(
            btn_frame,
            text="关闭",
            font=("Microsoft YaHei", 10),
            bg="#9E9E9E",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        # 启动后台分析
        start_analysis()


if __name__ == "__main__":
    root = tk.Tk()
    app = JunkCleaner(root)
    root.mainloop()
