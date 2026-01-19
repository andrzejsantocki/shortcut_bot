import json
import re
from typing import Any, Dict, Optional, List
import os
import sys

# ==============================================================
# TERMINAL COLORS
# ==============================================================
# helper regex to strip ANSI escapes when needed
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

class Colors:
    RESET = "\033[0m"

    BLACK = "\033[30m";      RED = "\033[31m";      GREEN = "\033[32m"
    YELLOW = "\033[33m";     BLUE = "\033[34m";      MAGENTA = "\033[35m"
    CYAN = "\033[36m";       WHITE = "\033[37m"

    BRIGHT_BLACK = "\033[90m";  BRIGHT_RED = "\033[91m";  BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"; BRIGHT_BLUE = "\033[94m"; BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m";   BRIGHT_WHITE = "\033[97m"


# ==============================================================
# THEMES
# ==============================================================

THEMES = {
    "chatgpt": {
        "key": Colors.BRIGHT_CYAN,
        "string": Colors.BRIGHT_GREEN,
        "number": Colors.BRIGHT_YELLOW,
        "boolean": Colors.BRIGHT_MAGENTA,
        "null": Colors.BRIGHT_BLACK,
        "bracket": Colors.BRIGHT_WHITE,
        "text": Colors.WHITE,
        "title": Colors.BRIGHT_CYAN,
        "md_header": Colors.BRIGHT_MAGENTA,
        "code": Colors.BRIGHT_GREEN,
        "xml_tag": Colors.BRIGHT_CYAN,
        "diff_add": Colors.BRIGHT_GREEN,
        "diff_del": Colors.BRIGHT_RED,
    },
    "matrix": {
        "key": Colors.GREEN,
        "string": Colors.BRIGHT_GREEN,
        "number": Colors.GREEN,
        "boolean": Colors.GREEN,
        "null": Colors.GREEN,
        "bracket": Colors.GREEN,
        "text": Colors.GREEN,
        "title": Colors.BRIGHT_GREEN,
        "md_header": Colors.BRIGHT_GREEN,
        "code": Colors.GREEN,
        "xml_tag": Colors.GREEN,
        "diff_add": Colors.GREEN,
        "diff_del": Colors.RED,
    },
    "monokai": {
        "key": Colors.YELLOW,
        "string": Colors.GREEN,
        "number": Colors.MAGENTA,
        "boolean": Colors.RED,
        "null": Colors.BRIGHT_BLACK,
        "bracket": Colors.WHITE,
        "text": Colors.WHITE,
        "title": Colors.YELLOW,
        "md_header": Colors.MAGENTA,
        "code": Colors.GREEN,
        "xml_tag": Colors.YELLOW,
        "diff_add": Colors.GREEN,
        "diff_del": Colors.RED,
    },
}

def enable_windows_ansi() -> bool:
    """
    Try to enable Windows ANSI (virtual terminal) processing.
    Returns True if successful (or not needed), False otherwise.
    """
    if os.name != "nt":
        return True  # non-Windows terminals typically support ANSI
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        hOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
        mode = ctypes.c_uint()
        if not kernel32.GetConsoleMode(hOut, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if not kernel32.SetConsoleMode(hOut, new_mode):
            return False
        return True
    except Exception:
        return False


def ensure_ansi_support():
    """
    Ensure ANSI codes will be rendered if possible.
    - On Windows: try kernel32 method, then colorama.init()
    - If ANSI cannot be enabled, we'll rely on later stripping.
    """
    # If stdout is not a TTY, many consoles/targets will not render ANSI.
    if not sys.stdout.isatty():
        # still try to enable on Windows, but we will fall back to strip later
        if os.name == "nt":
            enabled = enable_windows_ansi()
            if not enabled and colorama:
                colorama.init()
        return

    if os.name == "nt":
        if not enable_windows_ansi():
            if colorama:
                colorama.init()


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences for non-ANSI targets (files, GUI widgets)."""
    return _ANSI_RE.sub('', s)



# ==============================================================
# PAYLOAD FORMATTER (Core)
# ==============================================================

class PayloadFormatter:

    def __init__(self, theme: str = "chatgpt", indent: int = 2):
        if theme not in THEMES:
            raise ValueError(f"Unknown theme '{theme}'")
        self.theme = THEMES[theme]
        self.indent = indent

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def render(self, payload: Any) -> str:
        """
        Auto-detects: JSON, code-block markdown, XML/HTML, text, tool calls.
        """

        if isinstance(payload, dict) or isinstance(payload, list):
            return self.render_json(payload)

        if isinstance(payload, str):
            return self._render_text_or_json(payload)

        # fallback
        try:
            return self.render_json(json.dumps(payload))
        except:
            return str(payload)


    # ==============================================================
    # JSON RENDERER
    # ==============================================================

    def render_json(self, data: Any) -> str:
        """
        Colorizes a dict or JSON string.
        """
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                data = parsed
            except:
                return data  # not JSON

        text = json.dumps(data, indent=self.indent)
        return self._colorize_json(text)


    def _colorize_json(self, text: str) -> str:
        key = self.theme["key"]
        string = self.theme["string"]
        number = self.theme["number"]
        boolean = self.theme["boolean"]
        null = self.theme["null"]
        bracket = self.theme["bracket"]
        reset = Colors.RESET

        # 1. Brackets first (safe)
        text = re.sub(r'([\{\}\[\]])', lambda m: f"{bracket}{m.group(1)}{reset}", text)

        # 2. Keys
        text = re.sub(r'"(.*?)"(?=\s*:)', lambda m: f'{key}"{m.group(1)}"{reset}', text)

        # 3. Strings
        text = re.sub(r':\s*"(.*?)"', lambda m: f': {string}"{m.group(1)}"{reset}', text)

        # 4. Numbers
        text = re.sub(r'(?<=:\s)(-?\d+(\.\d+)?)', lambda m: f'{number}{m.group(1)}{reset}', text)

        # 5. Booleans
        text = re.sub(r'\btrue\b', f'{boolean}true{reset}', text)
        text = re.sub(r'\bfalse\b', f'{boolean}false{reset}', text)

        # 6. null
        text = re.sub(r'\bnull\b', f'{null}null{reset}', text)

        return text


    # ==============================================================
    # MARKDOWN RENDERER
    # ==============================================================

    def render_markdown(self, text: str) -> str:
        """
        Highlights headers and code blocks.
        """
        md_h = self.theme["md_header"]
        code_color = self.theme["code"]
        reset = Colors.RESET

        # Headers
        text = re.sub(r'^(#+)(.*)', lambda m: f"{md_h}{m.group(1)}{m.group(2)}{reset}", text, flags=re.MULTILINE)

        # Code blocks ```
        def code_block(match):
            code = match.group(1)
            return f"{code_color}{code}{reset}"

        text = re.sub(r"```(?:.*?\n)?(.*?)```", lambda m: code_block(m), text, flags=re.S | re.M)

        return text


    # ==============================================================
    # XML / HTML RENDERER
    # ==============================================================

    def render_xml(self, text: str) -> str:
        xml_color = self.theme["xml_tag"]
        reset = Colors.RESET

        # Highlight tags like <tag ...>
        text = re.sub(r"(</?[^>]+>)", lambda m: f"{xml_color}{m.group(1)}{reset}", text)
        return text


    # ==============================================================
    # CODE BLOCK FORMATTER (standalone)
    # ==============================================================

    def render_code(self, code: str) -> str:
        """
        Basic syntax highlight: comments, strings, numbers.
        """
        c = self.theme["code"]
        reset = Colors.RESET

        # Strings
        code = re.sub(r'"(.*?)"', lambda m: f'{c}"{m.group(1)}"{reset}', code)

        # Numbers
        code = re.sub(r"\b\d+\b", lambda m: f"{c}{m.group(0)}{reset}", code)

        # Comments (# ...)
        code = re.sub(r"#.*", lambda m: f"{Colors.BRIGHT_BLACK}{m.group(0)}{reset}", code)

        return code


    # ==============================================================
    # DIFF RENDERER
    # ==============================================================

    def render_diff(self, text: str) -> str:
        """
        Colors unified diff output.
        """
        add_c = self.theme["diff_add"]
        del_c = self.theme["diff_del"]
        reset = Colors.RESET

        lines = []
        for line in text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(f"{add_c}{line}{reset}")
            elif line.startswith("-") and not line.startswith("---"):
                lines.append(f"{del_c}{line}{reset}")
            else:
                lines.append(line)

        return "\n".join(lines)


    # ==============================================================
    # AUTO-DETECTOR: text / JSON / XML / Markdown
    # ==============================================================

    def _render_text_or_json(self, text: str) -> str:
        # JSON inside string
        try:
            parsed = json.loads(text)
            return self.render_json(parsed)
        except:
            pass

        # Markdown headers or code blocks?
        if "```" in text or text.strip().startswith("#"):
            return self.render_markdown(text)

        # XML / HTML?
        if "<" in text and ">" in text:
            if re.search(r"</?\w+[^>]*>", text):
                return self.render_xml(text)

        # fallback plain text
        return text


# ==============================================================
# CHAT HISTORY RENDERER (like ChatGPT logs)
# ==============================================================

class ChatHistory:
    """
    Stores multi-message interactions and renders them
    like ChatGPT conversation logs in the terminal.
    """

    def __init__(self, formatter: PayloadFormatter):
        self.formatter = formatter
        self.messages: List[Dict[str, Any]] = []

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.messages.append({"role": "assistant", "content": text})

    def add_system(self, text: str):
        self.messages.append({"role": "system", "content": text})

    def add_tool_call(self, payload: Dict[str, Any]):
        self.messages.append({"role": "tool", "content": payload})

    def print(self, force_strip: bool = False):
        """
        Print messages. Will auto-strip ANSI sequences when the target doesn't
        support them (non-tty) or when force_strip=True.
        """
        # Try enabling ANSI early (best-effort)
        ensure_ansi_support()

        role_colors = {
            "user": Colors.BRIGHT_BLUE,
            "assistant": Colors.BRIGHT_GREEN,
            "system": Colors.BRIGHT_MAGENTA,
            "tool": Colors.YELLOW
        }

        reset = Colors.RESET

        use_strip = force_strip or (not sys.stdout.isatty())

        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]

            header = f"\n{role_colors.get(role, Colors.WHITE)}[{role.upper()}]{reset}\n"
            if use_strip:
                header = strip_ansi(header)
            # print header
            sys.stdout.write(header)

            if isinstance(content, dict):
                out = self.formatter.render_json(content)
            else:
                out = self.formatter.render(content)

            if use_strip:
                out = strip_ansi(out)
            sys.stdout.write(out + "\n")
