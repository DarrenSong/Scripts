# pylauncher：双击 .py 不弹黑框
 
Windows 上双击 `.py` 会闪一个控制台窗口，`python xxx.py` 也一样。
这里给两种解法，都是零依赖的 VBS（wscript 是系统自带的）。
 
## 最快上手：复制 + 改名
 
把 `pyw.vbs` 复制到目标脚本旁边，改成**同名**：
 
```
D:\tools\report.py
D:\tools\report.vbs      <- 就是改名后的 pyw.vbs
```
 
双击 `report.vbs` 即可，用 `pythonw.exe` 跑，不弹任何窗口。
 
## 更省事：一键生成
 
```bash
python make_vbs.py                    # 当前目录所有 .py 各配一个同名 .vbs
python make_vbs.py pet.py             # 只给指定脚本配
python make_vbs.py pet.py -n 启动工具.vbs   # 输出名随便起（目标已写进文件头）
python make_vbs.py --generic          # 只要一个通用版 pyw.vbs
```
 
生成出来的启动器顶部有一行 `Const TARGET_PY = "xxx.py"`，
所以启动器**不必**和脚本同名，叫中文名也行。
 
## 启动器支持的开关
 
启动器自己吃掉、不会传给 Python：
 
| 开关 | 作用 |
| --- | --- |
| `/wait` | 等脚本结束，并把退出码返回给 wscript/cscript |
| `/show` | 显示控制台窗口（调试用，改用 python.exe） |
| `/py` | 强制用 python.exe，但窗口仍然隐藏（个别库要 stdin 时用） |
 
其余参数原样传给脚本，带空格和中文的都没问题。
 
```bat
wscript report.vbs --day 2026-09-17 "带 空 格"
cscript //nologo report.vbs /wait        &  echo %errorlevel%
```
 
环境变量 `PYW_PATH` 可以直接指定 `pythonw.exe` 的完整路径，优先级最高。
 
## 找 Python 的顺序
 
1. 环境变量 `PYW_PATH`
2. `PATH` 里的 `pythonw.exe`
3. `pyw.exe` / `py.exe` 启动器（`%WINDIR%`、`%LOCALAPPDATA%\Programs\Python\Launcher`）
4. 常见安装目录（`%LOCALAPPDATA%\Programs\Python\Python3xx`、`C:\Python3xx` 等，取版本号最大的）
5. 兜底用 `python.exe`（窗口仍然隐藏）
 
工作目录会设成脚本所在目录，脚本里的相对路径才不会看运气。
 
## 编码这件事
 
`pyw.src.txt` 是 UTF-8 的源模板，`make_vbs.py` 输出时统一转成
**UTF-16 LE 带 BOM**。原因：Windows Script Host 只认 ANSI 或 UTF-16，
UTF-8 保存的中文注释在 MsgBox 里会变乱码。直接改 `pyw.vbs` 也行，
但别用 UTF-8 存，改完记得用 `make_vbs.py --generic` 重新出一份。
 
报错信息在 cscript 下走纯 ASCII 分支，避免 GBK 控制台的乱码；
双击（wscript）时则用中文 MsgBox。
 
## 自测
 
双击 `selftest\hello.vbs`，几秒后同目录出现 `hello_out.json`，
里面记录了解析器、工作目录和收到的参数，即证明「无窗口启动 + 传参」都成立。