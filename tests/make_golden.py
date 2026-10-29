"""Create tests/data/golden_lc10_30_10.json from the REFERENCE implementation's spike file.

Run first: python scripts/check_own_core.py --impl eon   (writes /tmp/spikes_eon.npz)
Optionally also: python scripts/check_own_core.py --impl own   (the script then cross-checks the own core).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_core_full import summarize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "data" / "golden_lc10_30_10.json"


def main():
    ref = np.load("/tmp/spikes_eon.npz")
    summary = summarize(ref["i"], ref["t"])
    own_file = Path("/tmp/spikes_own.npz")
    if own_file.exists():
        own = np.load(own_file)
        same = summarize(own["i"], own["t"]) == summary
        print(f"own-core file present: summary identical to the reference: {same}")
        if not same:
            raise SystemExit("own core and reference differ; not writing the golden file")
    import brian2
    GOLDEN.write_text(json.dumps(dict(
        stimulus="LC10 left 30 Hz / right 10 Hz for 0.3 s, then 0.2 s without input; brain seed 1; "
                 "Poisson input adds 68.75 mV per spike, rfc = 0 for driven neurons (scripts/check_own_core.py)",
        source="reference implementation (spike file written by scripts/check_own_core.py --impl eon)",
        brian2_version=brian2.__version__, summary=summary), indent=2) + "\n")
    print(f"wrote {GOLDEN}\n{json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
