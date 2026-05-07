from lazurite.compiler.macro_define import MacroDefine
import sys

try:
    m = MacroDefine.from_string("TEST=1.2.3")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
