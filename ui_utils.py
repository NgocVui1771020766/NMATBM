import shutil, time, datetime, config
from net_utils import info

# ----- In bảng yêu cầu gốc -----
def print_requirement_table():
    cols = shutil.get_terminal_size().columns
    ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*cols)
    print(f"Requirement Tracking – launched at {ts}")
    print("="*cols)
    print("| {0:<35}| {1:^10}| {2:<30}|".format(
          "Nhóm yêu cầu gốc", "Status", "Vị trí hiện thực"))
    print("|" + "-"*35 + "+" + "-"*10 + "+" + "-"*30 + "|")
    for name, status, loc in config.REQUIREMENTS:
        print(f"| {name:<35}| {status:^10}| {loc:<30}|")
    print("="*cols + "\n")

# ----- Step tracker -----
class StepTracker:
    def __init__(self, total: int):
        self.total = total
        self.idx   = 0

    def next(self, desc: str):
        self.idx += 1
        info(f"[STEP {self.idx}/{self.total}] {desc} …")
        time.sleep(0.3)           # delay nhẹ để dễ đọc

    def done(self, action: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        info(f"[SUCCESS] {action} completed at {ts}\n")
