#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统资源监控器
实时显示 CPU、内存、网络、磁盘使用情况
显示占用资源前 10 的进程，支持杀死进程
"""

import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import time
import threading


class SystemMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("系统资源监控器")
        self.root.geometry("900x1000")
        self.root.configure(bg="#f0f0f0")

        # 网络速率计算
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        # CPU 手动计算：用 cpu_times 两次快照差值算百分比
        self.last_cpu_times = psutil.cpu_times()
        self.last_cpu_time_ts = time.time()

        self.setup_ui()
        self.schedule_update()

    def setup_ui(self):
        # 标题
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="系统资源监控器",
            font=("Microsoft YaHei", 18, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title_label.pack(pady=10)

        # 系统资源面板
        resource_frame = tk.Frame(self.root, bg="#f0f0f0")
        resource_frame.pack(fill=tk.X, padx=20, pady=10)

        # CPU 使用率
        self.create_resource_bar(resource_frame, "CPU", 0, "#e74c3c")

        # 内存使用率
        self.create_resource_bar(resource_frame, "内存", 1, "#3498db")

        # 磁盘使用率
        self.create_resource_bar(resource_frame, "磁盘", 2, "#2ecc71")

        # 网络信息
        net_frame = tk.Frame(resource_frame, bg="#f0f0f0")
        net_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        tk.Label(
            net_frame,
            text="网络:",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#f0f0f0",
            width=8,
            anchor="w"
        ).pack(side=tk.LEFT)

        self.net_label = tk.Label(
            net_frame,
            text="↑ 0 B/s  ↓ 0 B/s",
            font=("Consolas", 10),
            bg="#f0f0f0"
        )
        self.net_label.pack(side=tk.LEFT, padx=10)

        # 控制按钮区域（先 pack 到窗口底部，确保始终可见）
        control_frame = tk.Frame(self.root, bg="#f0f0f0")
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        # 杀死进程
        tk.Label(
            control_frame,
            text="进程 PID:",
            font=("Microsoft YaHei", 10),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.pid_entry = tk.Entry(
            control_frame,
            font=("Consolas", 11),
            width=15,
            relief="solid",
            bd=1
        )
        self.pid_entry.pack(side=tk.LEFT, padx=(0, 10))

        kill_btn = tk.Button(
            control_frame,
            text="杀死进程",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#e74c3c",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=12,
            command=self.kill_process
        )
        kill_btn.pack(side=tk.LEFT, padx=5)

        # 退出按钮
        exit_btn = tk.Button(
            control_frame,
            text="退出",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#95a5a6",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=12,
            command=self.root.quit
        )
        exit_btn.pack(side=tk.RIGHT, padx=5)

        # 进程列表（放在按钮之后，fill=BOTH expand=True 填充剩余空间）
        process_frame = tk.Frame(self.root, bg="#f0f0f0")
        process_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(
            process_frame,
            text="资源占用 Top 30 进程",
            font=("Microsoft YaHei", 13, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 5))

        # Treeview 样式
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Consolas", 10))
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))

        # 进程表格
        columns = ("pid", "name", "cpu", "memory")
        self.tree = ttk.Treeview(process_frame, columns=columns, show="headings", height=15)

        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="进程名")
        self.tree.heading("cpu", text="CPU %")
        self.tree.heading("memory", text="内存 MB")

        self.tree.column("pid", width=100, anchor="center")
        self.tree.column("name", width=300, anchor="w")
        self.tree.column("cpu", width=150, anchor="center")
        self.tree.column("memory", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(process_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 点击选中行时自动填充 PID
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 交替行颜色
        self.tree.tag_configure('odd', background='#ecf0f1')
        self.tree.tag_configure('even', background='#ffffff')

    def create_resource_bar(self, parent, name, row, color):
        """创建资源使用率进度条"""
        tk.Label(
            parent,
            text=f"{name}:",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#f0f0f0",
            width=8,
            anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=5)

        bar_frame = tk.Frame(parent, bg="#bdc3c7", height=25)
        bar_frame.grid(row=row, column=1, sticky="ew", pady=5, padx=(10, 0))

        if name == "CPU":
            self.cpu_bar = tk.Frame(bar_frame, bg=color, height=25)
            self.cpu_bar.place(relx=0, rely=0, relheight=1, relwidth=0)
            self.cpu_label = tk.Label(
                bar_frame,
                text="0%",
                font=("Consolas", 10, "bold"),
                bg=color,
                fg="white"
            )
            self.cpu_label.place(relx=0, rely=0, relheight=1, relwidth=0)
        elif name == "内存":
            self.mem_bar = tk.Frame(bar_frame, bg=color, height=25)
            self.mem_bar.place(relx=0, rely=0, relheight=1, relwidth=0)
            self.mem_label = tk.Label(
                bar_frame,
                text="0%",
                font=("Consolas", 10, "bold"),
                bg=color,
                fg="white"
            )
            self.mem_label.place(relx=0, rely=0, relheight=1, relwidth=0)
        elif name == "磁盘":
            self.disk_bar = tk.Frame(bar_frame, bg=color, height=25)
            self.disk_bar.place(relx=0, rely=0, relheight=1, relwidth=0)
            self.disk_label = tk.Label(
                bar_frame,
                text="0%",
                font=("Consolas", 10, "bold"),
                bg=color,
                fg="white"
            )
            self.disk_label.place(relx=0, rely=0, relheight=1, relwidth=0)

    def format_bytes(self, bytes_per_sec):
        """格式化字节为可读字符串"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_per_sec < 1024:
                return f"{bytes_per_sec:.1f} {unit}/s"
            bytes_per_sec /= 1024
        return f"{bytes_per_sec:.1f} TB/s"

    def schedule_update(self):
        """定时触发数据采集"""
        t = threading.Thread(target=self.collect_data, daemon=True)
        t.start()
        self.root.after(2000, self.schedule_update)

    def collect_data(self):
        """后台线程：采集所有系统数据，然后回调主线程刷新 UI"""
        # CPU：用两次 cpu_times 快照差值计算，完全非阻塞
        now = time.time()
        cpu_times = psutil.cpu_times()
        dt = now - self.last_cpu_time_ts
        if dt > 0:
            delta_idle = (cpu_times.idle + getattr(cpu_times, 'iowait', 0)) - \
                         (self.last_cpu_times.idle + getattr(self.last_cpu_times, 'iowait', 0))
            delta_total = sum(getattr(cpu_times, f) for f in cpu_times._fields) - \
                          sum(getattr(self.last_cpu_times, f) for f in self.last_cpu_times._fields)
            cpu_percent = (1.0 - delta_idle / delta_total) * 100.0 if delta_total > 0 else 0.0
        else:
            cpu_percent = 0.0
        self.last_cpu_times = cpu_times
        self.last_cpu_time_ts = now

        # 内存
        mem = psutil.virtual_memory()
        mem_percent = mem.percent

        # 磁盘
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # 网络
        current_net = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_time
        upload_speed = 0
        download_speed = 0
        if time_delta > 0:
            upload_speed = (current_net.bytes_sent - self.last_net.bytes_sent) / time_delta
            download_speed = (current_net.bytes_recv - self.last_net.bytes_recv) / time_delta
        self.last_net = current_net
        self.last_time = current_time

        # 进程列表
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'] or 'N/A',
                    'cpu': info['cpu_percent'] or 0,
                    'memory': info['memory_info'].rss / 1024 / 1024 if info['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        top_processes = processes[:30]

        # 回到主线程更新 UI
        self.root.after(0, self.apply_data, cpu_percent, mem_percent, disk_percent,
                        upload_speed, download_speed, top_processes)

    def apply_data(self, cpu_percent, mem_percent, disk_percent,
                   upload_speed, download_speed, top_processes):
        """主线程：用采集好的数据刷新 UI"""
        # CPU
        self.cpu_bar.place(relwidth=cpu_percent / 100)
        self.cpu_label.place(relwidth=cpu_percent / 100)
        self.cpu_label.config(text=f"{cpu_percent:.1f}%")

        # 内存
        self.mem_bar.place(relwidth=mem_percent / 100)
        self.mem_label.place(relwidth=mem_percent / 100)
        self.mem_label.config(text=f"{mem_percent:.1f}%")

        # 磁盘
        self.disk_bar.place(relwidth=disk_percent / 100)
        self.disk_label.place(relwidth=disk_percent / 100)
        self.disk_label.config(text=f"{disk_percent:.1f}%")

        # 网络
        self.net_label.config(
            text=f"↑ {self.format_bytes(upload_speed)}  ↓ {self.format_bytes(download_speed)}"
        )

        # 进程列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, proc in enumerate(top_processes):
            tag = 'odd' if idx % 2 else 'even'
            self.tree.insert(
                '',
                'end',
                values=(
                    proc['pid'],
                    proc['name'][:40],
                    f"{proc['cpu']:.1f}%",
                    f"{proc['memory']:.1f} MB"
                ),
                tags=(tag,)
            )

    def on_tree_select(self, event):
        """选中进程行时自动填充 PID"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            pid = item['values'][0]
            self.pid_entry.delete(0, tk.END)
            self.pid_entry.insert(0, str(pid))

    def kill_process(self):
        """杀死指定 PID 的进程"""
        pid_str = self.pid_entry.get().strip()

        if not pid_str:
            messagebox.showwarning("警告", "请输入进程 PID")
            return

        try:
            pid = int(pid_str)
        except ValueError:
            messagebox.showerror("错误", "PID 必须是数字")
            return

        try:
            process = psutil.Process(pid)
            name = process.name()
            process.terminate()
            process.wait(timeout=3)
            messagebox.showinfo("成功", f"已终止进程: {name} (PID: {pid})")
        except psutil.NoSuchProcess:
            messagebox.showerror("错误", f"进程不存在: PID {pid}")
        except psutil.AccessDenied:
            messagebox.showerror("错误", f"权限不足，无法终止进程: PID {pid}")
        except Exception as e:
            messagebox.showerror("错误", f"终止进程失败: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SystemMonitor(root)
    root.mainloop()
