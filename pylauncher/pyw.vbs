Option Explicit
' 由 make_vbs.py 写入：要启动的目标脚本名（留空则按「和自己同名」的规则找）
Const TARGET_PY = ""
' ===================================================================
'  通用 Python 静默启动器（不弹 cmd / 控制台窗口）
' -------------------------------------------------------------------
'  用法一（推荐）：把本文件复制成和目标脚本同名，放同一目录
'                  mytool.py  +  mytool.vbs   ->  双击 mytool.vbs
'  用法二：保留名字 pyw.vbs，把目标脚本当参数传
'                  wscript pyw.vbs D:\x\mytool.py arg1 "arg 2"
'  用法三：做快捷方式 / 计划任务时带参数
'                  wscript //nologo mytool.vbs --day 2026-09-16
'
'  启动器自己吃掉的开关（不会传给 Python）：
'      /wait   等脚本跑完，并把退出码返回给 wscript/cscript
'      /show   显示控制台窗口（调试用，等价于用 python.exe 跑）
'      /py     强制用 python.exe（窗口仍然隐藏），个别库需要 stdin 时用
'
'  可选环境变量：
'      PYW_PATH = 指定 pythonw.exe 的完整路径，优先级最高
'
'  找解释器顺序：PYW_PATH -> PATH 里的 pythonw -> pyw.exe 启动器
'                -> 常见安装目录 -> python.exe（隐藏窗口兜底）
'
'  注意：本文件请以「UTF-16 LE 带 BOM」或 ANSI 保存，UTF-8 保存会让
'        中文注释在 wscript 里乱码。用 encode_vbs.py 一键转换。
' ===================================================================
 
Dim sh, fso, selfPath, selfBase, workDir, target, py
Dim i, a, passArgs, optWait, optShow, optPy, firstArg
Dim style, cmdLine
 
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
 
selfPath = WScript.ScriptFullName
workDir = fso.GetParentFolderName(selfPath)
selfBase = fso.GetBaseName(selfPath)
 
optWait = False
optShow = False
optPy = False
passArgs = ""
firstArg = ""
 
For i = 0 To WScript.Arguments.Count - 1
    a = WScript.Arguments(i)
    If firstArg = "" Then firstArg = a
    Select Case LCase(a)
        Case "/wait", "-wait"
            optWait = True
        Case "/show", "-show"
            optShow = True
        Case "/py", "-py"
            optPy = True
        Case Else
            If passArgs <> "" Then passArgs = passArgs & " "
            passArgs = passArgs & Q(a)
    End Select
Next
 
' ---------- 1. 定位要跑的 .py ----------
Dim alt, cand
target = ""
If TARGET_PY <> "" Then
    ' 启动器可以叫任何名字（比如中文名），目标写在文件头里
    If fso.FileExists(fso.BuildPath(workDir, TARGET_PY)) Then
        target = fso.BuildPath(workDir, TARGET_PY)
    ElseIf fso.FileExists(AbsPath(TARGET_PY)) Then
        target = AbsPath(TARGET_PY)
    End If
End If
If target = "" And fso.FileExists(fso.BuildPath(workDir, selfBase & ".py")) Then
    target = fso.BuildPath(workDir, selfBase & ".py")
ElseIf firstArg <> "" And LCase(fso.GetExtensionName(firstArg)) = "py" _
        And fso.FileExists(AbsPath(firstArg)) Then
    ' pyw.vbs 模式：第一个参数就是目标脚本
    target = AbsPath(firstArg)
    passArgs = DropFirst(passArgs)
Else
    For Each alt In Array("main.py", "__main__.py", selfBase & ".pyw")
        cand = fso.BuildPath(workDir, alt)
        If fso.FileExists(cand) Then
            target = cand
            Exit For
        End If
    Next
End If
 
If target = "" Then
    Fail "找不到要启动的 Python 脚本" & vbCrLf & vbCrLf & _
         "launcher : " & selfPath & vbCrLf & _
         "folder   : " & workDir & vbCrLf & _
         "expected : " & ExpectDesc() & vbCrLf & vbCrLf & _
         "也可以：wscript //nologo " & fso.GetFileName(selfPath) & " 目标.py 参数..."
    WScript.Quit 2
End If
 
' ---------- 2. 定位解释器 ----------
py = ResolvePy(optShow Or optPy)
If py = "" Then
    Fail "找不到 Python 解释器。装好 Python 后重试，" & _
         "或把环境变量 PYW_PATH 指向 pythonw.exe 的完整路径。"
    WScript.Quit 3
End If
 
' ---------- 3. 启动 ----------
' 工作目录设成脚本所在目录，相对路径才不会看运气
On Error Resume Next
sh.CurrentDirectory = fso.GetParentFolderName(target)
On Error GoTo 0
 
style = 0
If optShow Then style = 1
 
cmdLine = Q(py) & " " & Q(target)
If passArgs <> "" Then cmdLine = cmdLine & " " & passArgs
 
If optWait Then
    WScript.Quit sh.Run(cmdLine, style, True)
Else
    sh.Run cmdLine, style, False
End If
 
 
' ===================================================================
'  工具函数
' ===================================================================
 
Function Q(s)
    Q = Chr(34) & s & Chr(34)
End Function
 
Function AbsPath(p)
    On Error Resume Next
    AbsPath = fso.GetAbsolutePathName(p)
    If Err.Number <> 0 Then AbsPath = p
    Err.Clear
    On Error GoTo 0
End Function
 
' 去掉参数串里第一个已加引号的参数
Function DropFirst(s)
    Dim q1, q2
    q1 = InStr(s, Chr(34))
    If q1 = 0 Then
        DropFirst = s
        Exit Function
    End If
    q2 = InStr(q1 + 1, s, Chr(34))
    If q2 = 0 Then
        DropFirst = ""
        Exit Function
    End If
    DropFirst = Trim(Mid(s, q2 + 1))
End Function
 
Function Env(name)
    Dim v
    v = sh.ExpandEnvironmentStrings("%" & name & "%")
    If InStr(v, "%") > 0 Then v = ""      ' 没设这个变量时原样返回
    Env = v
End Function
 
Function ResolvePy(needConsole)
    Dim fname, p, launcher
    fname = "pythonw.exe"
    If needConsole Then fname = "python.exe"
 
    ' 1) 环境变量指定
    p = Trim(Env("PYW_PATH"))
    If p <> "" And fso.FileExists(p) Then
        ResolvePy = p
        Exit Function
    End If
 
    ' 2) PATH
    p = ScanPath(fname)
    If p <> "" Then
        ResolvePy = p
        Exit Function
    End If
 
    ' 3) py 启动器（pyw.exe 相当于 pythonw）
    For Each launcher In Array("pyw.exe", "py.exe")
        p = ScanPath(launcher)
        If p = "" Then
            p = FirstExisting(Array(Env("WINDIR") & "\" & launcher, _
                                    Env("LOCALAPPDATA") & "\Programs\Python\Launcher\" & launcher))
        End If
        If p <> "" Then
            ResolvePy = p
            Exit Function
        End If
    Next
 
    ' 4) 常见安装目录
    p = ProbeInstalls(fname)
    If p <> "" Then
        ResolvePy = p
        Exit Function
    End If
 
    ' 5) 兜底：python.exe（窗口仍然隐藏）
    If Not needConsole Then
        p = ScanPath("python.exe")
        If p <> "" Then
            ResolvePy = p
            Exit Function
        End If
    End If
    ResolvePy = ""
End Function
 
Function ScanPath(fname)
    Dim parts, d, f
    parts = Split(Env("PATH"), ";")
    For Each d In parts
        If Trim(d) <> "" Then
            f = fso.BuildPath(Trim(d), fname)
            If fso.FileExists(f) Then
                ScanPath = f
                Exit Function
            End If
        End If
    Next
    ScanPath = ""
End Function
 
Function FirstExisting(arr)
    Dim k
    FirstExisting = ""
    For Each k In arr
        If k <> "" And fso.FileExists(k) Then
            FirstExisting = k
            Exit Function
        End If
    Next
End Function
 
Function ProbeInstalls(fname)
    Dim roots, root, k, flat, subs, subF, hit, ver, bestVer, best
    ' 兼容两种安装习惯：%LOCALAPPDATA%\Programs\Python\Python311\ 和 C:\Python311\
    roots = Array(Env("LOCALAPPDATA") & "\Programs\Python", "C:\Python", _
                  Env("ProgramFiles") & "\Python")
    bestVer = -1
    best = ""
    For Each root In roots
        If root <> "" And fso.FolderExists(root) Then
            On Error Resume Next
            Set subs = fso.GetFolder(root).SubFolders
            If Err.Number = 0 Then
                For Each subF In subs
                    ver = VerNum(subF.Name)
                    If ver > bestVer Then
                        hit = fso.BuildPath(subF.Path, fname)
                        If fso.FileExists(hit) Then
                            bestVer = ver
                            best = hit
                        End If
                    End If
                Next
            End If
            Err.Clear
            On Error GoTo 0
        End If
        For Each k In Array("38", "39", "310", "311", "312", "313", "314", "315")
            flat = root & k
            If root <> "" And fso.FolderExists(flat) Then
                ver = VerNum(fso.GetFileName(flat))
                If ver > bestVer Then
                    hit = fso.BuildPath(flat, fname)
                    If fso.FileExists(hit) Then
                        bestVer = ver
                        best = hit
                    End If
                End If
            End If
        Next
    Next
    ProbeInstalls = best
End Function
 
' 从 Python311 / Python313-32 这种目录名里取数字做版本比较
Function VerNum(name)
    Dim digits, i2, c
    digits = ""
    For i2 = 1 To Len(name)
        c = Mid(name, i2, 1)
        If c >= "0" And c <= "9" Then digits = digits & c
    Next
    If digits = "" Then
        VerNum = -1
    Else
        VerNum = CInt(digits)
    End If
End Function
 
Function ExpectDesc()
    If TARGET_PY <> "" Then
        ExpectDesc = TARGET_PY
    Else
        ExpectDesc = selfBase & ".py  (or main.py / __main__.py)"
    End If
End Function
 
Sub Fail(msg)
    If InStr(LCase(WScript.FullName), "cscript") > 0 Then
        ' cscript 控制台不是 UTF-8，中文会乱码，这里只输出 ASCII
        WScript.Echo "[pyrun] ERROR: cannot start the python script."
        WScript.Echo "[pyrun]   launcher : " & selfPath
        WScript.Echo "[pyrun]   folder   : " & workDir
        WScript.Echo "[pyrun]   expected : " & ExpectDesc()
        WScript.Echo "[pyrun]   usage    : wscript //nologo launcher.vbs [args]"
        WScript.Echo "[pyrun]   flags    : /wait  /show  /py      env: PYW_PATH"
    Else
        MsgBox msg, 48, "Python 启动器"
    End If
End Sub