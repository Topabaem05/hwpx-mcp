from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: install-local-model.py <backend-root> <model-id> <model-dir-name> <target-root>",
            file=sys.stderr,
        )
        return 2

    backend_root = Path(sys.argv[1]).resolve()
    model_id = sys.argv[2]
    model_dir_name = sys.argv[3]
    target_root = Path(sys.argv[4]).resolve()
    target_dir = target_root / model_dir_name

    sys.path[:0] = [
        str(backend_root),
        str(backend_root / "Lib" / "site-packages"),
    ]

    os.environ.setdefault("HF_HOME", str(target_root.parent / "hf"))
    target_dir.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=model_id, local_dir=str(target_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
