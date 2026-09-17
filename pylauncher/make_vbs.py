# -*- coding: utf-8 -*-
r"""给 .py 生成同名（或任意名字）的 .vbs 静默启动器，不弹 cmd 窗口。
用法：
    python make_vbs.py                    # 当前目录所有 .py 各配一个 .vbs
    python make_vbs.py pet.py             # 只给指定脚本配
    python make_vbs.py --generic          # 生成通用版 pyw.vbs（按同名规则或传参启动）
    python make_vbs.py pet.py -n 启动工具.vbs   # 指定输出文件名
    python make_vbs.py -d D:\proj         # 换目录
原理：模板 pyw.src.txt 里有个 TARGET_PY 常量，生成时写死目标脚本名，
所以启动器可以叫任何名字（包括中文名），不必和 .py 同名。
输出统一转成 UTF-16 LE 带 BOM：wscript 只认 ANSI 或 UTF-16，
UTF-8 保存的中文注释在弹窗里会乱码。
"""
import argparse
import codecs
import os
import sys
 
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "pyw.src.txt")
 
 
def emit(py_path, out_path=None, generic=False):
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        txt = f.read()
    target = "" if generic else os.path.basename(py_path)
    txt = txt.replace("@TARGET@", target)
    if out_path is None:
        if generic:
            out_path = os.path.join(os.path.dirname(py_path) or HERE, "pyw.vbs")
        else:
            out_path = os.path.splitext(py_path)[0] + ".vbs"
    elif not os.path.isabs(out_path):
        out_path = os.path.join(os.path.dirname(py_path) or HERE, out_path)
    with open(out_path, "wb") as f:
        f.write(codecs.BOM_UTF16_LE + txt.encode("utf-16-le"))
    return out_path
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="*", help="目标 .py，不给就扫目录")
    ap.add_argument("-d", "--dir", default=HERE, help="扫描目录")
    ap.add_argument("-n", "--name", help="输出 vbs 文件名（只对单个目标有效）")
    ap.add_argument("--generic", action="store_true", help="生成通用版 pyw.vbs")
    a = ap.parse_args()
 
    if not os.path.exists(TEMPLATE):
        print("缺少模板:", TEMPLATE)
        return 1
 
    targets = []
    for s in a.scripts:
        p = s if os.path.isabs(s) else os.path.join(a.dir, s)
        if os.path.exists(p):
            targets.append(os.path.abspath(p))
        else:
            print("跳过（不存在）:", s)
    if not targets and not a.generic:
        targets = [os.path.abspath(os.path.join(a.dir, n))
                   for n in sorted(os.listdir(a.dir))
                   if n.lower().endswith(".py") and not n.startswith("_")]
 
    made = []
    if a.generic:
        base = targets[0] if targets else os.path.join(HERE, "placeholder.py")
        made.append(emit(base, out_path=a.name, generic=True))
    for t in targets:
        if os.path.basename(t).lower() in ("make_vbs.py", "setup.py"):
            continue
        made.append(emit(t, out_path=a.name if len(targets) == 1 else None))
 
    if not made:
        print("没有生成任何文件。")
    for m in made:
        print("已生成:", m)
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())