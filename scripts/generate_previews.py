"""
Script to generate PDF previews for all templates.
Requires Windows with Hancom Office installed.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hwpx_mcp.tools.windows_hwp_controller import get_hwp_controller
except ImportError:
    print("Error: This script requires Windows environment.")
    sys.exit(1)

TEMPLATE_DIR = "templates"
PREVIEW_DIR = os.path.join("templates", "previews")

def main():
    print("Connecting to HWP...")
    ctrl = get_hwp_controller()
    if not ctrl:
        print("Error: Could not load HWP controller.")
        return
        
    if not ctrl.connect():
        print("Error: Could not connect to HWP.")
        return

    if not os.path.exists(PREVIEW_DIR):
        os.makedirs(PREVIEW_DIR)
        print(f"Created {PREVIEW_DIR}")

    files = sorted([f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".hwpx")])
    
    for i, f in enumerate(files):
        src = os.path.abspath(os.path.join(TEMPLATE_DIR, f))
        dst_name = os.path.splitext(f)[0] + ".pdf"
        dst = os.path.abspath(os.path.join(PREVIEW_DIR, dst_name))
        
        print(f"[{i+1}/{len(files)}] Converting {f} -> {dst_name}...")
        
        if ctrl.open(src):
            if ctrl.save_as_format(dst, "PDF"):
                print("  Success")
            else:
                print("  Failed to save PDF")
            ctrl.close_document()
        else:
            print("  Failed to open")

    print("All done!")

if __name__ == "__main__":
    main()
