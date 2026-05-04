#!/usr/bin/env python3
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_extract(args):
    from extraction.merger import merge_project
    merge_project(args.input, args.output, args.name)


def cmd_export(args):
    from export.obsidian import export
    export(args.graph, args.out)


def main():
    parser = argparse.ArgumentParser(prog="caeser")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ext = sub.add_parser("extract", help="Extract codebase → JSON graph")
    p_ext.add_argument("--input",  required=True, help="Project root directory")
    p_ext.add_argument("--output", required=True, help="Output JSON path")
    p_ext.add_argument("--name",                  help="Project name (default: folder name)")

    p_exp = sub.add_parser("export", help="Export graph → Obsidian vault")
    p_exp.add_argument("--graph", required=True, help="Input JSON graph path")
    p_exp.add_argument("--out",   required=True, help="Obsidian vault directory")

    args = parser.parse_args()
    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "export":
        cmd_export(args)


if __name__ == "__main__":
    main()
