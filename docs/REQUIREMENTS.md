# 手柄按键映射采集工具需求文档

## 1. 背景和目标

用户手里有多个不同型号的手柄，需要在后续开发前弄清楚每个手柄的按键、摇杆、扳机、十字键在程序中分别对应什么输入编号，并能保存成可复用的映射文件。

本工具的核心目标不是把手柄映射成键盘鼠标，也不是做虚拟手柄，而是解决三个开发前置问题：

1. 看懂手柄原始输入：随便按一个键，程序能告诉用户它是 `button 0`、`axis 3` 还是 `hat 0 up`。
2. 形成标准语义映射：把不同手柄的实际输入编号映射到统一名称，如 `a`、`b`、`leftx`、`righttrigger`，方便后续代码按统一字段读取。
3. 可视化测试和校准：界面显示一个通用手柄布局，用户按下真实手柄按钮时，对应的软件按钮高亮；如果识别不一致，用户可以在界面上重新绑定。

## 2. 用户和使用场景

主要用户是后续要写手柄控制逻辑的开发者，默认运行环境是 Windows + conda Python 3.12。

典型流程：

1. 用户连接一个手柄。
2. 运行设备列表命令，确认程序能识别手柄。
3. 运行图形界面，看到当前设备编号、设备名称和通用 Xbox 风格手柄图。
4. 用户按真实手柄按钮，界面上对应的软件按钮高亮。
5. 如果物理按钮与软件高亮位置不一致，用户点击界面上的目标按钮，再按真实物理按钮进行重新绑定。
6. 保存后工具输出 JSON、Markdown 报告和 SDL mapping string。
7. 后续开发代码读取 JSON，把不同手柄统一成同一套控制字段。

## 3. 功能需求

### 3.1 可视化测试与校准界面

命令：

```powershell
python -m controller_mapper gui
```

可选参数：

```powershell
python -m controller_mapper gui --device 0 --mapping mappings\example.json --output-dir mappings
```

需求：

- 界面显示一个通用 Xbox 风格手柄布局。
- 第一版界面不显示 `back`、`guide/home`、`start`，也不显示独立的 `LX/LY/RX/RY` 小按钮。
- 十字键不显示 `UP/DOWN/LEFT/RIGHT` 英文，改用 `↑/↓/←/→` 箭头。
- 左右摇杆放在界面下侧同一水平线上；十字键组和 ABXY 按键组也保持水平对齐的视觉关系。
- 十字键组和 ABXY 按键组相对上一版左移，避免按键贴近右侧边缘。
- 扳机和肩键相对上一版下移到手柄本体上方/边缘，不能遮挡顶部设备信息和映射路径文字。
- 保存和退出按钮需要有按下反馈：鼠标按下时按钮应变暗并轻微下沉，鼠标松开后再执行保存或退出。
- 摇杆推动必须直接驱动界面上的摇杆圆点移动，即使当前映射文件里 `leftx/lefty/rightx/righty` 还没有绑定。
- 界面上方显示当前连接设备编号和名称，例如 `[0] Xbox 360 Controller`。
- 界面上方同时显示 GUID 和当前映射文件状态。
- 用户按下真实手柄按钮、推动摇杆、按下扳机或十字键时，界面上对应的软件控件应实时高亮。
- 界面下方显示最近一次原始输入，例如 `raw: button 0 pressed` 或 `raw: axis 2 = +0.00 -> +0.76`。
- 用户能够通过高亮结果判断“自己按下的物理按钮”和“软件识别到的标准按钮”是否一致。
- 若识别不一致，用户可点击界面上的目标按钮，再按下实际对应的物理输入完成重新绑定。
- 未加载映射文件时，界面仍可显示原始输入，并允许用户通过点击目标按钮逐项建立映射。
- 用户可点击保存按钮或按 `S` 保存映射文件。
- 保存时继续输出 JSON、Markdown 报告和 SDL mapping string，并继续遵守 `.bak` 备份策略。
- 按 `Esc` 取消当前校准；没有正在校准的项目时，`Esc` 退出窗口。

### 3.2 设备列表

命令：

```powershell
python -m controller_mapper list
```

需求：

- 列出已连接手柄。
- 显示设备编号、名称、GUID、axis 数量、button 数量、hat 数量。
- 如果没有手柄，给出中文提示。
- 不显示 pygame 默认欢迎语，避免用户误以为程序出错。

### 3.3 实时输入监视

命令：

```powershell
python -m controller_mapper monitor
```

需求：

- 这是用户理解手柄输入的第一入口。
- 用户不需要先做映射，按任意键/推任意摇杆即可看到原始输入。
- 输出应尽量直观，例如：

```text
button 0 pressed
button 0 released
axis 0 = 0.82
axis 2 = -1.00 -> 0.36
hat 0 = up
```

- 支持 Ctrl+C 退出。
- 默认只显示变化的输入，避免屏幕刷满。
- 可选提供 `--all` 模式，周期性显示所有 button/axis/hat 当前状态。

### 3.4 交互式映射向导

命令：

```powershell
python -m controller_mapper map --write-sdl
```

需求：

- 向导使用中文主提示，英文 SDL 控件名作为辅助信息。
- 每一步明确说明：
  - 当前正在标定第几项。
  - 这一项对应手柄上的哪个物理控件。
  - 用户现在应该先松开所有按键，再按回车开始监听。
  - 监听开始后，在限定时间内按下或推动目标控件。
- 支持命令：
  - 回车：开始采集或确认检测结果。
  - `r`：重试当前项。
  - `s`：跳过当前项。
  - `q`：取消整个映射，不写入半成品文件。
- 检测到输入后，不只显示 `b0`，还要解释含义，例如：

```text
检测到 b0：第 0 号按钮
如果这是 A 键，直接回车确认；否则输入 r 重试。
```

- 对 Xbox/Windows 下可能无法读取的 Guide/Home 键，提示用户可以跳过。

### 3.5 映射验证

命令：

```powershell
python -m controller_mapper validate --mapping mappings/example.json
```

需求：

- 读取已保存 JSON 映射。
- 实时显示标准化后的控件状态。
- 只显示活跃控件，便于用户逐项核对。
- 支持 `--json` 输出完整状态，方便后续程序调试。

### 3.6 SDL 映射导出

命令：

```powershell
python -m controller_mapper export-sdl --mapping mappings/example.json
```

需求：

- 从 JSON 生成 SDL-compatible mapping string。
- 支持写入 `.sdl.txt` 文件。
- 控件命名对齐 SDL/Xbox 风格。

## 4. 标准控件范围

第一版覆盖以下控件：

- 面部按键：`a`、`b`、`x`、`y`
- 功能按键：`back`、`start`、`guide`
- 肩键：`leftshoulder`、`rightshoulder`
- 摇杆按下：`leftstick`、`rightstick`
- 扳机：`lefttrigger`、`righttrigger`
- 摇杆轴：`leftx`、`lefty`、`rightx`、`righty`
- 十字键：`dpup`、`dpdown`、`dpleft`、`dpright`

## 5. 数据输出

每个手柄输出独立文件：

```text
mappings/<device>_<guid>.json
mappings/<device>_<guid>.md
mappings/<device>_<guid>.sdl.txt
```

JSON 至少包含：

- `schema_version`
- `created_at`
- `device`
  - `name`
  - `guid`
  - `instance_id`
  - `axes`
  - `buttons`
  - `hats`
- `controls`
  - 标准控件名到物理输入编号的映射
  - 示例：`"a": "b0"`、`"leftx": "a0"`、`"dpup": "h0.1"`
- `normalization`
  - `deadzone`
  - `capture_threshold`
  - `axis_directions`
  - `trigger_ranges`

## 6. 归一化规则

后续开发读取映射后，应得到统一字段：

- button：`true` / `false`
- stick axis：`-1.0` 到 `1.0`
- trigger：`0.0` 到 `1.0`
- dpad：`true` / `false`

默认参数：

- deadzone：`0.15`
- capture threshold：`0.45`

十字键需要兼容三种设备表现：

- button
- hat
- axis

## 7. 非功能需求

- 默认面向 Windows 本机。
- 推荐 conda 环境：Python 3.12。
- 运行时只依赖 `pygame`。
- 单元测试不依赖真实手柄。
- 不需要管理员权限。
- 输出文件使用 UTF-8。
- 覆盖已有映射前生成 `.bak` 备份。

## 8. 非目标范围

第一版不做：

- 键盘/鼠标重映射。
- 虚拟 XInput 手柄。
- 手柄震动/灯光控制。
- 自动上传或同步社区数据库。
- 复杂配置编辑器。

## 9. 验收标准

### 9.1 基础验收

- 在 conda `controller-map` 环境中运行 `python -m controller_mapper list` 能识别 Xbox 360 Controller。
- 输出不出现 pygame 欢迎语。
- 无手柄时显示清晰中文提示。

### 9.2 图形界面验收

- 运行 `python -m controller_mapper gui` 后弹出 Pygame 窗口。
- 窗口顶部显示 `[0] Xbox 360 Controller`、GUID 和当前映射状态。
- 界面中部显示通用 Xbox 风格手柄布局。
- 按真实手柄 A/B/X/Y 时，界面对应按钮高亮。
- 推左右摇杆时，界面摇杆圆点跟随原始 axis 值移动。
- 按左右扳机时，界面 LT/RT 有可见反馈。
- 按十字键时，界面对应方向高亮。
- 点击界面 A 后按真实 A，可将 A 重新绑定到检测到的物理输入。
- 保存后生成 JSON、Markdown 和 SDL 文本文件。
- 关闭再打开 GUI 时，已保存映射能被自动加载或通过 `--mapping` 加载。

### 9.3 监视模式验收

- 运行 `python -m controller_mapper monitor` 后，按 A/B/X/Y 能看到对应 button press/release。
- 推左右摇杆能看到 axis 数值变化。
- 按十字键能看到 hat 或 button/axis 变化。
- Ctrl+C 能正常退出。

### 9.4 映射向导验收

- 用户能仅凭中文提示完成一次 Xbox 360 Controller 映射。
- 每一步都能跳过、重试或确认。
- Guide/Home 键无法读取时可跳过，不影响完成映射。
- 完成后生成 JSON、Markdown 报告和 SDL 文本文件。

### 9.5 后续开发验收

- 后续代码能读取 JSON 映射。
- 给定原始 button/axis/hat 状态，能输出统一标准字段。
- 同一个开发逻辑不需要关心具体手柄的 button/axis 编号。

## 10. 当前实现状态

当前应具备：

- `list`
- `monitor`
- `map`
- `gui`
- `validate`
- `export-sdl`
- Pygame 可视化手柄测试与校准界面
- JSON/Markdown/SDL 输出
- 核心归一化逻辑和单元测试
- pygame 欢迎语隐藏
- 中文主提示的映射向导
- `b0`、`a2`、`h0.1` 等原始编号解释
- 面向使用者的中文 README

仍需通过真实手柄人工验收：

1. `gui` 窗口是否能正常显示手柄布局、设备编号和设备名称。
2. `gui` 下按键、摇杆、扳机、十字键变化是否都能高亮到正确控件。
3. `gui` 中点击目标按钮并按真实物理输入后，是否能完成重新绑定并保存。
4. `monitor` 下按键、摇杆、扳机、十字键变化是否都能被看到。
5. `map --write-sdl` 是否能仅凭中文提示完成一次完整映射。
6. `validate` 输出的标准字段是否与实际手柄操作一致。
7. 生成的 SDL mapping string 是否满足后续目标工具链使用。
