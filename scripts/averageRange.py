#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prints information related to surfaces in the format:
    [".vtk", ".vtp", ".ply", ".stl", ".xml", ".obj"]

Script prints amount of vertices, triangles and its bounding box
"""

import re
import argparse

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

    ranges = []

    with open(filename, "r") as f:
        for line in f:
            # Use regex to find the number before ' m'
            match = re.search(r"Range:\s*([\d.]+)\s*m", line)
            if match:
                value = float(match.group(1))
                ranges.append(value)

    if ranges:
        avg = sum(ranges) / len(ranges)
        print(f"Average range: {avg:.3f} m over {len(ranges)} measurements")
    else:
        print("No range values found in the file.")

if __name__ == "__main__":
    main()
