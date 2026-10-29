"""
Terminal UI helpers -- colors, banners, prompts, formatting.
Pure stdlib, no external dependencies.

Adapted from sonnet's modular-architecture ui.py for grafika:
same scroll-region chatbox model, grafika banner + status fields.
"""
import io
import os
import sys
import shutil

# Force UTF-8 on Windows so box-drawing doesn't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

# ── ANSI Color Codes ──────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
ITALIC  = "\033[3m"

RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"

BG_RED     = "\033[41m"
BG_GREEN   = "\033[42m"
BG_BLUE    = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN    = "\033[46m"

# -- Icons (ASCII-safe for Windows cp1252 compat) -----------------
ICON_SUCCESS = f"{GREEN}+{RESET}"
ICON_ERROR   = f"{RED}x{RESET}"
ICON_WARN    = f"{YELLOW}!{RESET}"
ICON_INFO    = f"{CYAN}>{RESET}"
ICON_ARROW   = f"{MAGENTA}>{RESET}"

# -- Capability detection -------------------------------------------
# Advanced mode (scroll regions + bottom chatbox) needs a VT-capable tty.
# Anything else (pipes, legacy conhost, dumb terms) gets plain line mode
# so output never shows raw escape codes like in the bug report.
_FORCE_PLAIN = False


def set_plain(on: bool = True) -> None:
    """Force plain line-mode TUI. Also honored via GRAFIKA_PLAIN=1 env."""
    global _FORCE_PLAIN
    _FORCE_PLAIN = on


def _vt_ready() -> bool:
    """Try enabling virtual-terminal processing on Windows. Cached."""
    global _VT_CACHE
    try:
        return _VT_CACHE
    except NameError:
        pass
    ok = False
    if os.name != "nt":
        ok = True
    else:
        try:
            kernel32 = __import__("ctypes").windll.kernel32
            h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = __import__("ctypes").c_ulong()
            if kernel32.GetConsoleMode(h, __import__("ctypes").byref(mode)):
                ok = bool(mode.value & 0x0004) or bool(
                    kernel32.SetConsoleMode(h, mode.value | 0x0004))
        except Exception:
            ok = False
    _VT_CACHE = ok
    return ok


def advanced() -> bool:
    """True when the terminal can handle scroll regions + chatbox."""
    if _FORCE_PLAIN or os.environ.get("GRAFIKA_PLAIN") == "1":
        return False
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    return _vt_ready()


if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
    # Strip colors for pipes/files/dumb terms; harmless when tty.
    try:
        if not sys.stdout.isatty():
            RESET = BOLD = DIM = ITALIC = ""
            RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
            BG_RED = BG_GREEN = BG_BLUE = BG_MAGENTA = BG_CYAN = ""
            ICON_SUCCESS, ICON_ERROR, ICON_WARN, ICON_INFO, ICON_ARROW = "+", "x", "!", ">", ">"
    except Exception:
        pass


def get_terminal_width():
    """
    Dynamically computes terminal width so UI elements don't wrap
    unexpectedly on resize. Falls back to 80 cols safely.
    """
    return shutil.get_terminal_size((80, 24)).columns


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def _apply_gradient(text):
    """Apply a violet-to-cyan horizontal gradient to the ASCII art."""
    lines = text.splitlines()
    if not lines:
        return text

    max_len = max(len(line) for line in lines)
    if max_len == 0:
        return text

    # Violet (167, 139, 250) to Cyan (0, 255, 255)
    r1, g1, b1 = 167, 139, 250
    r2, g2, b2 = 0, 255, 255

    result = []
    for line in lines:
        colored_line = ""
        for i, char in enumerate(line):
            ratio = i / max_len if max_len > 0 else 0
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            colored_line += f"\033[38;2;{r};{g};{b}m{char}"
        colored_line += f"{RESET}"
        result.append(colored_line)

    return "\n".join(result)


def _draw_banner(h, w):
    """
    Renders the responsive grafika branding based on available vertical space.
    Returns the line where the scrolling history should start so the logo
    remains anchored at the top of the viewport.
    """
    if h >= 28:
        # Full banner, 5-row block glyphs (no trailing spaces: editor-safe)
        art = (
            " ██████  ██████    ██████  ██████   ██████ ██   ██   ██████\n"
            "██       ██   ██  ██   ██  ██         ██   ██  ██   ██   ██\n"
            "██   ███ ██████   ███████  ██████     ██   █████    ███████\n"
            "██   ██  ██  ██   ██   ██  ██         ██   ██  ██   ██   ██\n"
            " ██████  ██   ██  ██   ██  ██       ██████ ██   ██  ██   ██"
        )
        print(f"\n{_apply_gradient(art)}\n")
        print(f"  {DIM}extract > compile > inject > reset{DIM}{RESET}")
        print()
        scroll_start = 12
    else:
        print(f"  {BOLD}{CYAN}> GRAFIKA{RESET} {DIM}extract > compile > inject > reset{RESET}\n")
        scroll_start = 5

    print(f"{DIM}{'─' * (w - 1)}{RESET}\n")

    return scroll_start


def separator(char="-", color=DIM):
    """
    Draws a full-width delimiter bounded to the active terminal size.
    Prevents text bleed between logically distinct sections.
    """
    w = get_terminal_width()
    print(f"{color}{char * (w - 1)}{RESET}")


def header(text):
    """Print a section header."""
    print(f"\n  {BOLD}{CYAN}{text}{RESET}")
    separator()


def success(text):
    """Print a success message."""
    print(f"  {ICON_SUCCESS} {GREEN}{text}{RESET}")


def error(text):
    """Print an error message."""
    print(f"  {ICON_ERROR} {RED}{text}{RESET}")


def warn(text):
    """Print a warning message."""
    print(f"  {ICON_WARN} {YELLOW}{text}{RESET}")


class CancelCommand(Exception):
    """Raised when the user cancels a prompt via Ctrl+C."""
    pass


def info(text):
    """Print an info message."""
    print(f"  {ICON_INFO} {text}")


def step(text):
    """Print a step/action indicator."""
    print(f"  {ICON_ARROW} {text}")


def prompt(label, default=None):
    """
    Synchronous blocking input that safely intercepts SIGINT (Ctrl+C).
    Raises CancelCommand to cleanly unwind back to the main loop instead
    of crashing the interpreter.
    """
    if default is not None:
        hint = f" {DIM}({default}){RESET}"
    else:
        hint = ""

    try:
        value = input(f"  {BOLD}{CYAN}{_prompt_icon()}{RESET} {label}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise CancelCommand()

    if advanced():
        print(f"\033[{_scroll_end};1H\n", end="", flush=True)
    if value == "" and default is not None:
        return default
    return value


def _prompt_icon():
    """
    Icon shown before every interactive prompt. Nerd Font chevron when the
    terminal can render it, '?' fallback for pipes/legacy conhost (cp1252
    cannot carry the glyph).
    """
    return "\uf105" if advanced() else "?"


def prompt_confirm(label, default=True):
    """Ask the user a yes/no question. Returns True/False."""
    hint = "Y/n" if default else "y/N"
    try:
        value = input(f"  {BOLD}{CYAN}{_prompt_icon()}{RESET} {label} {DIM}({hint}){RESET}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        raise CancelCommand()

    if advanced():
        print(f"\033[{_scroll_end};1H\n", end="", flush=True)
    if value == "":
        return default
    return value in ("y", "yes")


def prompt_choice(label, options, default=0):
    """
    Show a numbered menu and let the user pick.
    options: list of strings. default: 0-based index. Returns selected string.
    """
    print(f"\n  {BOLD}{CYAN}{_prompt_icon()}{RESET} {label}")
    for i, opt in enumerate(options):
        marker = f"{CYAN}*{RESET}" if i == default else f"{DIM}o{RESET}"
        default_tag = f" {DIM}(default){RESET}" if i == default else ""
        print(f"    {marker} {BOLD}{i + 1}{RESET}. {opt}{default_tag}")

    try:
        print(f"  {DIM}Enter choice [1-{len(options)}]{RESET}: ", end="", flush=True)
        value = input("").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise CancelCommand()

    if advanced():
        print(f"\033[{_scroll_end};1H\n", end="", flush=True)
    if value == "":
        return options[default]

    try:
        idx = int(value) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass

    warn(f"Invalid choice, using default: {options[default]}")
    return options[default]


def _get_workspace_name():
    """Current repo dir name for the status bar."""
    return os.path.basename(os.getcwd())


def _get_game_version():
    """Installed game version, cheap (XML parse only). None on failure."""
    try:
        import core
        v = core.game_version()
        return v if v != "unknown" else None
    except Exception:
        return None


def _get_base_count():
    """Number of serialized base JSONs, or None."""
    try:
        import core
        if not core.MATERIALS_JSON_DIR.is_dir():
            return None
        return len(list(core.MATERIALS_JSON_DIR.glob("*.material.json")))
    except Exception:
        return None


# Module-level scroll region state
_scroll_start = 18
_scroll_end = 20


def setup_tui():
    """
    Bootstraps the ANSI scrolling environment.
    Locks the top banner in place while isolating command output to the
    middle chunk of the terminal, preventing the chatbox from being overwritten.
    Falls back to a plain banner when the terminal can't do VT (pipes,
    legacy conhost) so output never shows raw escape codes.
    """
    global _scroll_start, _scroll_end
    if not advanced():
        print(f"  {BOLD}{CYAN}> GRAFIKA{RESET} {DIM}extract > compile > inject > reset{RESET}")
        print(f"  {DIM}(plain mode: limited terminal){RESET}\n")
        return
    # Nuke the entire screen AND scrollback buffer to prevent history bleed
    print("\033[2J\033[3J\033[H", end="")

    h = shutil.get_terminal_size((80, 24)).lines
    w = get_terminal_width()

    _scroll_start = _draw_banner(h, w)

    # Set scroll region from below banner to above prompt
    _scroll_end = max(_scroll_start + 2, h - 9)
    print(f"\033[{_scroll_start};{_scroll_end}r", end="")

    # Move cursor to the bottom of the scroll region
    print(f"\033[{_scroll_end};1H", end="")


def enter_scroll():
    """
    Repositions the hardware cursor back into the active scrolling zone.
    Must be called after rendering the chatbox (which lives in the static
    bottom pane) so standard prints flow into the history area.
    No-op in plain mode.
    """
    if not advanced():
        return
    print(f"\033[{_scroll_start};{_scroll_end}r", end="")
    print(f"\033[{_scroll_end};1H", end="")


def reset_tui():
    """
    Tears down the ANSI scroll margins before exit.
    Failing to reset would leave the user's shell permanently windowed
    to the middle of the screen. No-op in plain mode.
    """
    if not advanced():
        return
    h = shutil.get_terminal_size((80, 24)).lines
    print(f"\033[r\033[{h};1H", end="")


def prompt_shell():
    """
    Renders the persistent chatbox interface at the bottom of the screen.
    Uses absolute positioning so painting the UI grid never shifts the
    terminal's native history buffer. In plain mode uses a simple line prompt.
    """
    if not advanced():
        try:
            value = input("grafika> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            value = "exit"
        if value and value != "exit":
            print(f"> {value}")
        return value
    w = get_terminal_width()
    safe_w = w - 1  # Prevent scrollbar wrapping on Windows
    h = shutil.get_terminal_size((80, 24)).lines

    prompt_row = max(16, h - 8)
    clear_eol = "\033[K"

    shortcuts = "? for shortcuts"
    gap0 = max(1, safe_w - len(shortcuts))
    r1 = f"\033[{prompt_row};1H{' ' * gap0}{DIM}{shortcuts}{RESET}"
    r2 = f"\033[{prompt_row + 1};1H{DIM}{'─' * safe_w}{RESET}"
    top_left = "Type 'help' for commands"
    r3 = f"\033[{prompt_row + 2};1H{DIM}{top_left}{RESET}"
    r4 = f"\033[{prompt_row + 3};1H\033[38;5;237m{'▄' * w}{RESET}"

    bg = "\033[48;5;237m"
    r5_bg = f"\033[{prompt_row + 4};1H{bg}{' ' * w}{RESET}"
    r6 = f"\033[{prompt_row + 5};1H\033[38;5;237m{'▀' * w}{RESET}"
    r7 = f"\033[{prompt_row + 6};1H{clear_eol}"

    h1, v1 = "workspace (/directory)", os.getcwd()
    h2, v2 = "game", _get_game_version() or "unknown"
    n_base = _get_base_count()
    h3, v3 = "base", f"{n_base} json" if n_base is not None else "none"
    h4, v4 = "/engine", "grafika-core"

    cw1 = int(safe_w * 0.40)
    cw2 = int(safe_w * 0.20)
    cw3 = int(safe_w * 0.20)
    cw4 = safe_w - cw1 - cw2 - cw3

    if len(v1) > cw1 - 2:
        v1 = "..." + v1[-(cw1 - 5):]

    r8 = f"\033[{prompt_row + 7};1H{DIM}{h1:<{cw1}}{h2:<{cw2}}{h3:<{cw3}}{h4:<{cw4}}{RESET}"

    v3_colored = f"{MAGENTA}{BOLD}{v3:<{cw3}}{RESET}"
    v4_colored = f"{WHITE}{BOLD}{v4:<{cw4}}{RESET}"
    r9 = f"\033[{prompt_row + 8};1H{WHITE}{BOLD}{v1:<{cw1}}{v2:<{cw2}}{RESET}{v3_colored}{v4_colored}"

    # Draw all rows WITHOUT newlines to prevent terminal scrolling bugs!
    for row in (r1, r2, r3, r4, r5_bg, r6, r7, r8, r9):
        print(f"{row}{clear_eol}", end="", flush=True)

    prefix = f"\033[{prompt_row + 4};1H{bg} {MAGENTA}{BOLD}>{RESET}{bg} "
    print(f"{prefix}", end="", flush=True)

    try:
        value = input("")
    except (EOFError, KeyboardInterrupt):
        value = "exit"
        print()
    finally:
        print(RESET, end="")

    enter_scroll()

    if value and value != "exit":
        print(f"{DIM}> {value}{RESET}")

    return value.strip()


def show_command_table(commands):
    """
    Display available commands in a clean table.
    commands: list of (name, description) tuples.
    """
    max_name = max(len(name) for name, _ in commands)
    for name, desc in commands:
        padding = " " * (max_name - len(name) + 2)
        print(f"    {BOLD}{CYAN}{name}{RESET}{padding}{DIM}{desc}{RESET}")
