"""
Script to generate PDF and Image previews for all templates.
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
        base_name = os.path.splitext(f)[0]
        dst_pdf = os.path.abspath(os.path.join(PREVIEW_DIR, base_name + ".pdf"))
        dst_png = os.path.abspath(os.path.join(PREVIEW_DIR, base_name + ".png"))
        
        print(f"[{i+1}/{len(files)}] Processing {f}...")
        
        if ctrl.open(src):
            # 1. Generate PDF
            if not os.path.exists(dst_pdf):
                print(f"  -> PDF")
                ctrl.save_as_format(dst_pdf, "PDF")
            
            # 2. Generate PNG (Page 1)
            if not os.path.exists(dst_png):
                print(f"  -> PNG")
                # create_page_image(path, page=0, dpi=96, depth=24, fmt='png')
                ctrl.create_page_image(dst_png, 0, 150, 24, "png")
                
            ctrl.close_document()
        else:
            print("  Failed to open")

    print("All done!")

if __name__ == "__main__":
    main()
