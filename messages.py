import time
import sys

class Messages:
    def __init__(self, *args, **kwargs):
        self.RESET = "\033[0m"

        self.COLORS = {
            "info": "\033[38;5;39m",
            "warning": "\033[38;5;220m",
            "error": "\033[38;5;9m",
            "success": "\033[38;5;10m",
        }

        self.ICONS = {
            "info": "[i]",
            "warning": "[!]",
            "error": "[X]",
            "success": "[✓]",
        }

    def __print(self, kind: str, txt: str):
        timestamp = time.strftime("%H:%M:%S")
        color = self.COLORS.get(kind, "")
        icon = self.ICONS.get(kind, "[?]")
        print(f"{color}[{timestamp}] {icon} {txt}{self.RESET}")

    def info(self, txt: str):
        self.__print("info", txt)

    def warning(self, txt: str):
        self.__print("warning", txt)

    def error(self, txt: str):
        self.__print("error", txt)

    def success(self, txt: str):
        self.__print("success", txt)