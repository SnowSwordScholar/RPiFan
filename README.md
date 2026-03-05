# RPiFan (uv + PID + TUI)

这是一个使用 Python 编写的高性能树莓派风扇控制系统。
使用 **PID控制** 进行无级调速，采用 **前后端分离** 架构，通过 **内存共享** 通信，并集成 **TUI界面** 进行状态监控。

## ✨ 核心特性

*   **架构分离**：后台 Daemon (core logic) + 前端 TUI (status view)。
*   **内存通信**：使用 `/dev/shm` 内存映射交换状态，读写极快，不伤 SD 卡。
*   **PID 温控**：平滑调节风扇转速，精准控温。
*   **TUI 监控**：实时显示 CPU 温度、风扇转速、CPU 占用率、内存使用情况。
*   **Systemd集成**：完全自动启动，崩溃自愈。
*   **uv 管理**：现代化的 Python 项目依赖管理。

## 📁 目录结构

```
.
├── config.json           # 核心配置文件
├── fan-control.service   # Systemd 服务模板
├── rpifan.sh             # 快捷启动脚本
├── pyproject.toml        # UV 项目依赖定义
├── README.md             # 说明文档
└── src/
    ├── backend.py        # 后端 Daemon (PID, GPIO)
    ├── frontend.py       # 前端 TUI (Rich)
    └── shared.py         # 共享逻辑
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 依赖安装

进入项目目录并同步环境：

```bash
cd tempC
uv sync
```

### 3. 创建全局启动命令 (推荐)

为了在任何地方都能方便地打开 TUI 界面，我们可以创建一个全局命令。

1.  赋予脚本执行权限：
    ```bash
    chmod +x rpifan.sh
    ```

2.  创建软链接到系统路径 (例如 `/usr/local/bin`)：
    ```bash
    # 请确保你在项目根目录下执行此命令
    sudo ln -s $(pwd)/rpifan.sh /usr/local/bin/rpifan
    ```

现在，你可以在终端的任何位置输入 `rpifan` 来启动监控界面！

### 4. 测试运行

在一个终端启动后端（如果是首次）：

```bash
sudo uv run -m src.backend
```

在另一个终端启动前端界面（使用新命令）：

```bash
rpifan
```

## ⚙️ 部署自动启动 (Systemd)

本服务设计为后台 Daemon 运行，开机自启。

1.  **编辑服务文件**：根据实际路径修改 `fan-control.service`。
    重点修改 `WorkingDirectory` 和 `ExecStart`。
    
    ```ini
    # 示例
    WorkingDirectory=/home/pi/tempC
    ExecStart=/home/pi/.local/bin/uv run -m src.backend
    ```

2.  **安装服务**：

    ```bash
    sudo cp fan-control.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable fan-control
    sudo systemctl start fan-control
    ```

3.  **查看状态**：

    ```bash
    systemctl status fan-control
    # 或者直接使用我们的 TUI
    rpifan
    ```

## 🔧 配置调整

修改 `config.json` 后，需重启服务生效：

```bash
sudo systemctl restart fan-control
```

| 参数 | 说明 | 推荐值 |
| :--- | :--- | :--- |
| `target_temp` | 目标恒温值 | 55.0 |
| `min_duty_cycle` | 风扇最低启动转速(%) | 20-30 |
| `kp` | PID 比例系数 (响应速度) | 5.0 |
| `ki` | PID 积分系数 (消除误差) | 0.2 |
