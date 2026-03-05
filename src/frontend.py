import select
import sys
import termios
import tty
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich import box
from rich.progress import BarColumn, Progress, TextColumn
from rich.columns import Columns
import time
import json
import os
import psutil
import datetime

class FanMonitor:
    def __init__(self):
        self.console = Console()
        self.status_file = "/dev/shm/fan_status.json" if os.path.exists("/dev/shm") else "/tmp/fan_status.json"
        self.cpu_history = []
        
    def read_status(self):
        try:
            if not os.path.exists(self.status_file):
                return None
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except:
            return None

    def make_layout(self):
        layout = Layout(name="root")
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        # 左侧：温度 (上) + 风扇 (下)
        layout["left"].split(
            Layout(name="temp_box", ratio=2),
            Layout(name="fan_box", ratio=1)
        )
        # 右侧：系统 (上) + PID/Details (下)
        layout["right"].split(
            Layout(name="sys_box", ratio=1),
            Layout(name="pid_box", ratio=1)
        )
        return layout

    def get_temp_panel(self, status):
        if not status:
            return Panel(Align.center("[red bold]OFFLINE[/]"), title="CPU Temperature", border_style="red")
        
        temp = status.get('current_temp', 0)
        target = status.get('target_temp', 55)
        
        # Color coding
        if temp < target:
            color = "green"
            symbol = "❄️ COOL"
        elif temp < target + 5:
            color = "yellow"
            symbol = "⚠️ WARM"
        else:
            color = "red"
            symbol = "🔥 HOT!"

        # Big styled text
        grid = Table.grid(expand=True)
        grid.add_column(justify="center")
        grid.add_row(Text(f"{temp:.1f}°C", style=f"bold {color} reverse"))
        grid.add_row("")
        grid.add_row(Text(symbol, style="bold white"))
        grid.add_row(Text(f"Target: {target}°C", style="dim white"))
        
        return Panel(
            Align.center(grid, vertical="middle"), 
            title="CPU Temperature", 
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def get_fan_panel(self, status):
        
        duty = status.get('duty_cycle', 0) if status else 0
        is_running = duty > 0
        
        status_text = "ACTIVE" if is_running else "IDLE"
        color = "cyan" if is_running else "white"
        
        prog_bar = Progress(
            TextColumn("{task.percentage:>3.0f}%", style="cyan"),
            BarColumn(bar_width=None, complete_style="cyan", finished_style="green"), 
            expand=True
        )
        prog_bar.add_task("Speed", total=100, completed=duty)
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="center")
        
        status_line = Text()
        status_line.append("Fan: ", style="dim")
        status_line.append(status_text, style=f"bold {color}")
        
        grid.add_row(status_line)
        grid.add_row(prog_bar)
        
        return Panel(
            Align.center(grid, vertical="middle"),
            title="Fan Controller",
            border_style="cyan",
            box=box.ROUNDED
        )

    def get_system_panel(self):
        # 使用 psutil 获取本地系统信息
        cpu_pct = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        load_avg = os.getloadavg()
        
        table = Table(expand=True, box=None, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="white")

        # CPU Load Color
        cpu_color = "green"
        if cpu_pct > 80: cpu_color = "red"
        elif cpu_pct > 50: cpu_color = "yellow"
        
        table.add_row("Load Avg", f"{load_avg[0]:.2f} / {load_avg[1]:.2f} / {load_avg[2]:.2f}")
        table.add_row("CPU Usage", f"[{cpu_color}]{cpu_pct}%[/]")
        table.add_row("Memory", f"{mem.percent}%")
        table.add_row("Used", f"{mem.used / (1024**3):.1f} GB")
        table.add_row("Total", f"{mem.total / (1024**3):.1f} GB")
        
        return Panel(
            table,
            title="System Monitor",
            border_style="blue",
            box=box.ROUNDED
        )

    def get_pid_panel(self, status):
        if not status:
            return Panel(Align.center("Waiting for data..."), title="PID Control")

        table = Table(expand=True, box=None, show_header=False)
        table.add_column("Key", style="magenta")
        table.add_column("Value", justify="right", style="white")
        
        table.add_row("PID Out", f"{status.get('pid_output', 0):.2f}")
        table.add_row("P-Term", f"{status.get('pid_p')}")
        table.add_row("I-Term", f"{status.get('pid_i')}")
        table.add_row("D-Term", f"{status.get('pid_d')}")
        
        # Heartbeat
        now = time.time()
        updated = status.get('timestamp', 0)
        age = now - updated
        age_style = "green" if age < 2 else "red"
        
        table.add_section()
        table.add_row("Heartbeat", f"[{age_style}]{age:.2f}s ago[/]")

        return Panel(
            table,
            title="Control Loop",
            border_style="magenta",
            box=box.ROUNDED
        )

    def run(self):
        layout = self.make_layout()
        
        head = Text(" RPi Smart Fan Control System ", style="bold white on blue")
        layout["header"].update(Panel(Align.center(head), box=box.HEAVY, style="blue"))
        
        footer = Text("Press 'q' or Ctrl+C to minimize TUI", style="dim")
        layout["footer"].update(Panel(Align.center(footer), box=box.SIMPLE))

        # Check if stdin is a tty
        is_tty = sys.stdin.isatty()
        old_settings = None

        try:
            # Setup terminal
            if is_tty:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())

            with Live(layout, refresh_per_second=2, screen=True):
                while True:
                    # Check for key press
                    if is_tty:
                        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if rlist:
                            key = sys.stdin.read(1)
                            if key.lower() == 'q':
                                break

                    status = self.read_status()
                    
                    # Dynamic update
                    layout["left"]["temp_box"].update(self.get_temp_panel(status))
                    layout["left"]["fan_box"].update(self.get_fan_panel(status))
                    
                    layout["right"]["sys_box"].update(self.get_system_panel())
                    layout["right"]["pid_box"].update(self.get_pid_panel(status))
                    
                    # we can sleep here if necessary, or let select handle timing
                    if not is_tty:
                        time.sleep(0.5)

        finally:
            if is_tty and old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def main():
    try:
        FanMonitor().run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
