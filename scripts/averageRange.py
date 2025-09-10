import re
import argparse
from collections import defaultdict

def _build_arg_parser():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("in_file", help="Input filename.")
    return p

def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    filename = args.in_file

    # Dictionary: {anchor_id: [list of ranges]}
    ranges = defaultdict(list)

    with open(filename, "r") as f:
        for line in f:
            # Match "from: AAA1       Range: 3.36 m"
            match = re.search(r"from:\s*(\w+)\s+Range:\s*([\d.]+)\s*m", line)
            if match:
                anchor_id = match.group(1)
                value = float(match.group(2))
                ranges[anchor_id].append(value)

    if ranges:
        for anchor_id, values in ranges.items():
            avg = sum(values) / len(values)
            print(f"Anchor {anchor_id}: Average = {avg:.3f} m "
                  f"over {len(values)} measurements")
    else:
        print("No range values found in the file.")

if __name__ == "__main__":
    main()
