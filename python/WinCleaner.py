#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
360 风格 Windows 垃圾清理工具（Python + tkinter）
需要管理员权限才能清空回收站及系统临时文件夹
"""

import os
import sys
import shutil
import ctypes
import threading
import subprocess
import fnmatch
import platform
from tkinter import *
from tkinter import ttk, messagebox, filedialog

# ------------------------------------------------------------
# 垃圾清理引擎
# ------------------------------------------------------------
class GarbageCategory:
    """垃圾类别定义"""
    def __init__(self, name, description, paths, patterns=None, scan_func=None, clean_func=None):
        self.name = name
        self.description = description
        self.paths = paths or []          # 待扫描的目录列表
        self.patterns = patterns or ['*'] # 文件名匹配模式（glob 风格）
        self.scan_func = scan_func        # 自定义扫描函数（可选）
        self.clean_func = clean_func      # 自定义清理函数（可选）
        self.files = []                   # 扫描到的文件列表 (path, size)
        self.total_size = 0
        self.total_count = 0

class CleanerEngine:
    """垃圾扫描与清理引擎"""
    def __init__(self):
        self.categories = self._init_categories()

    def _init_categories(self):
        """初始化所有垃圾类别"""
        cat_list = []

        # 1. 系统临时文件
        temp_paths = [
            os.environ.get('TEMP', 'C:\\Windows\\Temp'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Temp')
        ]
        cat_list.append(GarbageCategory(
            "系统临时文件",
            "Windows 临时文件夹中的无用文件",
            temp_paths,
            patterns=['*.tmp', '*.temp', '*.log', '*.old', '*.bak']
        ))

        # 2. 回收站
        cat_list.append(GarbageCategory(
            "回收站",
            "回收站中的文件",
            [],
            clean_func=self._empty_recycle_bin,
            scan_func=self._scan_recycle_bin
        ))

        # 3. IE 浏览器缓存
        cat_list.append(GarbageCategory(
            "IE 浏览器缓存",
            "Internet Explorer 缓存文件",
            [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'INetCache')],
            patterns=['*']
        ))

        # 4. Chrome 缓存
        chrome_cache = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                    r'Google\Chrome\User Data\Default\Cache')
        cat_list.append(GarbageCategory(
            "Chrome 缓存",
            "Google Chrome 缓存文件",
            [chrome_cache],
            patterns=['*']
        ))

        # 5. Edge 缓存
        edge_cache = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                  r'Microsoft\Edge\User Data\Default\Cache')
        cat_list.append(GarbageCategory(
            "Edge 缓存",
            "Microsoft Edge 缓存文件",
            [edge_cache],
            patterns=['*']
        ))

        # 6. Windows 日志
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        cat_list.append(GarbageCategory(
            "Windows 日志",
            "系统日志文件 (*.log, *.etl)",
            [os.path.join(windir, 'Logs')],
            patterns=['*.log', '*.etl', '*.log1', '*.log2']
        ))

        # 7. 缩略图缓存
        thumb_path = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                  r'Microsoft\Windows\Explorer')
        cat_list.append(GarbageCategory(
            "缩略图缓存",
            "资源管理器缩略图缓存",
            [thumb_path],
            patterns=['thumbcache_*.db']
        ))

        # 8. Windows 更新缓存
        update_path = os.path.join(windir, 'SoftwareDistribution', 'Download')
        cat_list.append(GarbageCategory(
            "Windows Update 缓存",
            "Windows Update 下载的安装文件",
            [update_path],
            patterns=['*']
        ))

        # 9. 预读取文件
        cat_list.append(GarbageCategory(
            "预读取文件",
            "Prefetch 文件夹内容",
            [os.path.join(windir, 'Prefetch')],
            patterns=['*.pf']
        ))

        # 10. 最近文档记录
        recent = os.path.join(os.environ.get('APPDATA', ''),
                              r'Microsoft\Windows\Recent')
        cat_list.append(GarbageCategory(
            "最近文档记录",
            "开始菜单最近文档快捷方式",
            [recent],
            patterns=['*.lnk']
        ))

        # 11. 应用程序临时文件（QQ/微信等）
        local_appdata = os.environ.get('LOCALAPPDATA', '')
        app_temp_dirs = [
            os.path.join(local_appdata, 'Tencent', 'QQ', 'temp'),
            os.path.join(local_appdata, 'Tencent', 'WeChat', 'temp'),
            os.path.join(local_appdata, 'Microsoft', 'InputMethod', 'Chs')
        ]
        cat_list.append(GarbageCategory(
            "应用临时文件",
            "QQ、微信、输入法等临时文件",
            app_temp_dirs,
            patterns=['*.tmp', '*.temp', '*.cache']
        ))

        return cat_list

    def _scan_recycle_bin(self):
        """自定义扫描回收站（通过枚举 $Recycle.Bin）"""
        files = []
        recycle_path = os.path.join(os.environ.get('SystemDrive', 'C:'), '$Recycle.Bin')
        try:
            for root, dirs, filenames in os.walk(recycle_path):
                for f in filenames:
                    full = os.path.join(root, f)
                    try:
                        size = os.path.getsize(full)
                        files.append((full, size))
                    except OSError:
                        continue
        except PermissionError:
            pass
        return files

    def _empty_recycle_bin(self, files=None):
        """清空回收站（需要管理员权限）"""
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"清空回收站失败：{e}\n请以管理员身份运行程序。")
            return False

    def scan_category(self, category, progress_callback=None):
        """扫描一个类别，返回 (file_list, total_size)"""
        category.files = []
        category.total_size = 0
        category.total_count = 0

        if category.scan_func:
            files = category.scan_func()
            for path, size in files:
                category.files.append((path, size))
                category.total_size += size
                category.total_count += 1
            return

        for base_path in category.paths:
            if not os.path.exists(base_path):
                continue
            for root, dirs, filenames in os.walk(base_path):
                for pattern in category.patterns:
                    for f in fnmatch.filter(filenames, pattern):
                        full = os.path.join(root, f)
                        try:
                            size = os.path.getsize(full)
                            category.files.append((full, size))
                            category.total_size += size
                            category.total_count += 1
                        except (OSError, PermissionError):
                            continue
                if progress_callback:
                    progress_callback()
    def clean_category(self, category, progress_callback=None):
        """清理一个类别的垃圾文件，返回 (deleted_count, failed_count)"""
        if category.clean_func:
            result = category.clean_func(category.files)
            # 如果自定义清理函数返回布尔值，则转换为文件计数
            if isinstance(result, bool):
                if result:
                    return len(category.files), 0
                else:
                    return 0, len(category.files)
            else:
                # 假设返回的是 (deleted, failed) 元组
                return result
        
        deleted_count = 0
        failed = 0
        for path, size in category.files:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                deleted_count += 1
            except Exception:
                failed += 1
            if progress_callback:
                progress_callback()
        return deleted_count, failed

# ------------------------------------------------------------
# GUI 主界面
# ------------------------------------------------------------
class CleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows 垃圾清理工具 (Python)")
        self.root.geometry("750x650")
        self.root.resizable(True, True)

        self.engine = CleanerEngine()
        self.categories = self.engine.categories
        self.check_vars = []
        self.scanning = False
        self.cleaning = False

        self.create_widgets()
        self.update_disk_info()

    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, text="选择要清理的项目：", font=("Microsoft YaHei", 10, "bold")).pack(anchor=W)

        # 带滚动条的复选框区域
        canvas = Canvas(main_frame, height=260, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor=NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=TOP, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        for cat in self.categories:
            var = BooleanVar(value=True)
            self.check_vars.append(var)
            cb = ttk.Checkbutton(scroll_frame, text=f"{cat.name} - {cat.description}",
                                 variable=var, command=self.update_stats)
            cb.pack(anchor=W, pady=1)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=5)
        self.scan_btn = ttk.Button(btn_frame, text="扫描垃圾", command=self.start_scan)
        self.scan_btn.pack(side=LEFT, padx=5)
        self.clean_btn = ttk.Button(btn_frame, text="清理选中", command=self.start_clean, state=DISABLED)
        self.clean_btn.pack(side=LEFT, padx=5)
        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self.cancel_operation, state=DISABLED)
        self.cancel_btn.pack(side=LEFT, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate', length=600)
        self.progress.pack(fill=X, pady=5)

        # 状态信息
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=X)
        self.status_label = ttk.Label(info_frame, text="就绪")
        self.status_label.pack(side=LEFT)
        self.count_label = ttk.Label(info_frame, text="文件: 0 个")
        self.count_label.pack(side=LEFT, padx=20)
        self.size_label = ttk.Label(info_frame, text="释放空间: 0 B")
        self.size_label.pack(side=LEFT)

        # 结果列表
        columns = ("文件名", "类别", "大小")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=12)
        self.tree.heading("文件名", text="文件名")
        self.tree.heading("类别", text="类别")
        self.tree.heading("大小", text="大小")
        self.tree.column("文件名", width=300)
        self.tree.column("类别", width=150)
        self.tree.column("大小", width=100)
        self.tree.pack(fill=BOTH, expand=True, pady=5)

        # 滚动条 for treeview
        tree_scroll = ttk.Scrollbar(main_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=RIGHT, fill=Y)

    def update_disk_info(self):
        """更新标题显示磁盘剩余空间"""
        if platform.system() == "Windows":
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                os.environ.get('SystemDrive', 'C:') + '\\', None, None, ctypes.byref(free_bytes))
            free = free_bytes.value
            self.root.title(f"Windows 垃圾清理工具 - 剩余空间: {self.format_size(free)}")
        else:
            self.root.title("Windows 垃圾清理工具")

    def format_size(self, bytes):
        """字节转可读字符串"""
        if bytes >= 1073741824:
            return f"{bytes / 1073741824:.2f} GB"
        elif bytes >= 1048576:
            return f"{bytes / 1048576:.2f} MB"
        elif bytes >= 1024:
            return f"{bytes / 1024:.2f} KB"
        else:
            return f"{bytes} B"

    def update_stats(self):
        """更新底部统计信息（根据复选框选择计算）"""
        total_selected_size = 0
        total_selected_count = 0
        for i, cat in enumerate(self.categories):
            if self.check_vars[i].get():
                total_selected_size += cat.total_size
                total_selected_count += cat.total_count
        self.count_label.config(text=f"文件: {total_selected_count} 个")
        self.size_label.config(text=f"释放空间: {self.format_size(total_selected_size)}")

    def start_scan(self):
        """开始扫描（线程）"""
        if self.scanning or self.cleaning:
            return
        self.scanning = True
        self.scan_btn.config(state=DISABLED)
        self.clean_btn.config(state=DISABLED)
        self.cancel_btn.config(state=NORMAL)
        self.tree.delete(*self.tree.get_children())
        self.status_label.config(text="正在扫描...")
        self.progress['value'] = 0

        thread = threading.Thread(target=self._scan_thread, daemon=True)
        thread.start()

    def _scan_thread(self):
        """扫描线程体"""
        try:
            for idx, cat in enumerate(self.categories):
                if not self.scanning:  # 支持取消
                    return
                self.engine.scan_category(cat)
                # 更新进度
                self.root.after(0, lambda i=idx: self.progress.config(value=(i+1)*100/len(self.categories)))
            self.root.after(0, self._scan_finished)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"扫描出错：{e}"))
            self.root.after(0, self._reset_buttons)

    def _scan_finished(self):
        """扫描完成后的 UI 更新"""
        self.scanning = False
        self.scan_btn.config(state=NORMAL)
        self.clean_btn.config(state=NORMAL)
        self.cancel_btn.config(state=DISABLED)
        self.progress['value'] = 100
        self.status_label.config(text="扫描完成")

        # 填充列表
        for cat in self.categories:
            for path, size in cat.files:
                self.tree.insert("", END, values=(os.path.basename(path), cat.name, self.format_size(size)))

        self.update_stats()
        self.update_disk_info()

    def start_clean(self):
        """开始清理选中的类别"""
        if self.scanning or self.cleaning:
            return
        # 确认对话框
        if not messagebox.askyesno("确认清理", "确定要删除选中的垃圾文件吗？\n此操作不可撤销！"):
            return
        self.cleaning = True
        self.scan_btn.config(state=DISABLED)
        self.clean_btn.config(state=DISABLED)
        self.cancel_btn.config(state=NORMAL)
        self.status_label.config(text="正在清理...")
        self.progress['value'] = 0

        thread = threading.Thread(target=self._clean_thread, daemon=True)
        thread.start()

    def _clean_thread(self):
        """清理线程体"""
        try:
            total_deleted = 0
            total_failed = 0
            total_freed = 0
            selected_cats = [cat for i, cat in enumerate(self.categories) if self.check_vars[i].get()]

            for idx, cat in enumerate(selected_cats):
                if not self.cleaning:
                    return
                # 清理前记录大小
                freed_before = sum(size for _, size in cat.files)
                deleted, failed = self.engine.clean_category(cat)
                total_deleted += deleted
                total_failed += failed
                total_freed += freed_before  # 粗略计算，实际删除成功的才计数
                # 更新进度
                self.root.after(0, lambda i=idx, n=len(selected_cats): self.progress.config(value=(i+1)*100/n))

            # 清理完成后重置类别数据
            for cat in self.categories:
                cat.files = []
                cat.total_size = 0
                cat.total_count = 0

            self.root.after(0, lambda: self._clean_finished(total_deleted, total_failed, total_freed))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"清理出错：{e}"))
            self.root.after(0, self._reset_buttons)

    def _clean_finished(self, deleted, failed, freed):
        """清理完成后的 UI 更新"""
        self.cleaning = False
        self.scan_btn.config(state=NORMAL)
        self.clean_btn.config(state=DISABLED)  # 清理后列表清空，需重新扫描
        self.cancel_btn.config(state=DISABLED)
        self.progress['value'] = 100
        msg = f"清理完成！\n删除文件: {deleted} 个\n失败: {failed} 个\n释放空间: {self.format_size(freed)}"
        self.status_label.config(text=msg)
        messagebox.showinfo("清理完成", msg)
        self.tree.delete(*self.tree.get_children())
        self.update_stats()
        self.update_disk_info()

    def cancel_operation(self):
        """取消扫描或清理"""
        self.scanning = False
        self.cleaning = False
        self.scan_btn.config(state=NORMAL)
        self.clean_btn.config(state=NORMAL)
        self.cancel_btn.config(state=DISABLED)
        self.status_label.config(text="操作已取消")

    def _reset_buttons(self):
        """重置按钮状态"""
        self.scanning = False
        self.cleaning = False
        self.scan_btn.config(state=NORMAL)
        self.clean_btn.config(state=NORMAL)
        self.cancel_btn.config(state=DISABLED)

# ------------------------------------------------------------
# 程序入口
# ------------------------------------------------------------
if __name__ == "__main__":
    # 检查管理员权限（清空回收站需要）
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            messagebox.showwarning("提示", "建议以管理员身份运行本程序，否则可能无法清理系统目录和回收站。")
    except:
        pass

    root = Tk()
    app = CleanerApp(root)
    root.mainloop()
