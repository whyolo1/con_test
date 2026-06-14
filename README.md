# 手柄按键映射采集工具

这个工具用来帮你弄清楚不同手柄在程序里的真实输入编号，并把它们保存成统一的开发用映射。

它解决三个问题：

1. 我随便按一个手柄键，程序能告诉我它是哪个 `button`、`axis` 或 `hat`。
2. 我把不同手柄都标定成同一套字段，例如 `a`、`b`、`leftx`、`righttrigger`，后续开发代码就不用关心具体手柄型号。
3. 我可以在窗口里看到一个手柄图，按下真实手柄按钮时，对应的软件按钮会高亮；如果不一致，可以直接点击界面按钮重新绑定。

## 推荐环境

建议使用独立 conda 环境：

```powershell
conda create -n controller-map python=3.12 -y
conda activate controller-map
cd E:\BaiduSyncdisk\proj\con_test
python -m pip install -e .
```

运行时只依赖 `pygame`。测试使用 Python 标准库 `unittest`，不需要真实手柄。

## 第一步：确认手柄被识别

```powershell
python -m controller_mapper list
```

你应该看到类似：

```text
检测到以下手柄：
[0] Xbox 360 Controller
    guid=030003f05e0400008e02000000007200
    instance_id=0 axes=6 buttons=11 hats=1
```

如果没有手柄，程序会提示先连接手柄。

## 第二步：打开图形界面测试和校准

推荐优先使用图形界面：

```powershell
python -m controller_mapper gui
```

界面会显示：

- 顶部：当前设备编号、设备名称、GUID、映射文件状态
- 中间：通用 Xbox 风格手柄图
- 底部：最近一次原始输入和操作提示

基本操作：

- 按真实手柄按钮：界面上对应按钮会高亮。
- 推摇杆/按扳机/按十字键：界面上对应控件会有状态反馈。
- 如果高亮位置和你按的物理按钮不一致：点击界面上的目标按钮，再按真实物理按钮重新绑定。
- 按 `S` 或点击“保存”：写出 JSON、Markdown 报告和 SDL 映射文件。
- 按 `Esc`：取消当前校准；没有正在校准时退出窗口。

可选参数：

```powershell
python -m controller_mapper gui --device 0
python -m controller_mapper gui --mapping mappings\你的映射文件.json
python -m controller_mapper gui --output-dir mappings
```

## 可选：查看原始输入

如果你想看最底层的 `button/axis/hat` 编号，可以使用：

```powershell
python -m controller_mapper monitor
```

然后随便按手柄按键、推动摇杆或按十字键，程序会显示原始输入编号：

```text
button 0 pressed
button 0 released
axis 0 = +0.00 -> +0.82
hat 0 = up
```

含义：

- `button 0`：第 0 号按钮
- `axis 0`：第 0 号轴，通常是摇杆或扳机
- `hat 0`：第 0 个十字键/帽开关

退出监视：按 `Ctrl+C`。

如果想周期性显示全部输入状态：

```powershell
python -m controller_mapper monitor --all
```

## 可选：命令行正式生成映射

```powershell
python -m controller_mapper map --write-sdl
```

流程是：

1. 选择手柄，只有一个手柄时直接回车。
2. 每一步先松开所有按键和摇杆。
3. 按回车开始监听。
4. 按提示操作手柄上的目标按键/摇杆/扳机/十字键。
5. 检测正确就直接回车确认。

可用命令：

- 回车：开始采集或确认检测结果
- `r`：重试当前项
- `s`：跳过当前项
- `q`：取消整个映射，不写入半成品文件

提示：Xbox/Windows 下 Guide/Home 键有时读不到，遇到这一步可以输入 `s` 跳过。

完成后会生成：

```text
mappings/<device>_<guid>.json
mappings/<device>_<guid>.md
mappings/<device>_<guid>.sdl.txt
```

## 验证映射

```powershell
python -m controller_mapper validate --mapping mappings\你的映射文件.json
```

它会显示标准化后的控件状态，例如：

```text
{'a': True}
{'leftx': 0.76}
```

如果后续程序想直接读取完整状态：

```powershell
python -m controller_mapper validate --mapping mappings\你的映射文件.json --json
```

## 导出 SDL 映射字符串

```powershell
python -m controller_mapper export-sdl --mapping mappings\你的映射文件.json
```

这个字符串可用于兼容 SDL 风格映射的工具链。

## 映射文件格式

标准控件名使用 SDL/Xbox 风格：

```text
a, b, x, y,
back, start, guide,
leftshoulder, rightshoulder,
leftstick, rightstick,
lefttrigger, righttrigger,
leftx, lefty, rightx, righty,
dpup, dpdown, dpleft, dpright
```

物理输入编号使用：

- `b0`：第 0 号按钮
- `a3`：第 3 号轴
- `+a0` / `-a0`：某个轴的正向或负向
- `h0.1`：第 0 个 hat 的上方向

归一化规则：

- button：`true` / `false`
- stick axis：`-1.0` 到 `1.0`
- trigger：`0.0` 到 `1.0`
- dpad：`true` / `false`

## 测试

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```
