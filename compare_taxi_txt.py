#!/usr/bin/env python3
"""
Compare ABC-style invoice text vs TaxiCalendar booking export text.

Answers: for each trip on the invoice, is there a matching booking in the
calendar export? Only trips on the invoice that do NOT appear in the calendar
file are listed (same match key: date + time + normalised driver).

Standalone Windows app (build with build_taxi_compare_txt.cmd → TaxiCompareTxt.exe).
Same idea as WeeklyCircularProcessor.exe: double-click the .exe, no Python, no .cmd.
Writes TaxiCompare_Result.txt in the Compare folder.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Trip:
    """One parsed trip for comparison."""

    key: str
    ymd: str
    time_hhmm: str
    driver_display: str
    detail: str

    def line(self) -> str:
        return f"{self.ymd} {self.time_hhmm}  {self.driver_display}  |  {self.detail}"


def _norm_driver(name: str) -> str:
    n = name.strip().upper().replace("'", " ")
    return " ".join(n.split())


def _hhmm(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


def _parse_hhmm(s: str) -> str:
    a, b = s.strip().split(":", 1)
    return _hhmm(int(a), int(b))


# Invoice: optional "Date " prefix; optional "Time " before clock; IRISH RAIL - NAME then From: or €
_INV_LINE = re.compile(
    r"(?im)^[^\S\r\n]*(?:Date\s+)?(\d{1,2}-[A-Za-z]{3}-\d{2})\s+(?:Time\s+)?(\d{1,2}:\d{2})\b.*?"
    r"IRISH\s+RAIL\s*-\s*(.+?)(?:\s+From:|\s+\u20ac\s*\d|\s+€\s*\d|\s*$)",
)


def parse_invoice_text(text: str) -> list[Trip]:
    out: list[Trip] = []
    for m in _INV_LINE.finditer(text):
        d_raw, t_raw, drv_raw = m.group(1), m.group(2), m.group(3)
        drv_raw = drv_raw.strip()
        if not drv_raw or re.match(r"^Details\s*$", drv_raw, re.I):
            continue
        try:
            dt = datetime.strptime(d_raw, "%d-%b-%y")
        except ValueError:
            try:
                dt = datetime.strptime(d_raw.title(), "%d-%b-%y")
            except ValueError:
                continue
        ymd = dt.strftime("%Y%m%d")
        hhmm = _parse_hhmm(t_raw)
        nd = _norm_driver(drv_raw)
        key = f"{ymd}|{hhmm}|{nd}"
        snippet = re.sub(r"\s+", " ", m.group(0).strip())[:160]
        out.append(Trip(key=key, ymd=ymd, time_hhmm=hhmm, driver_display=nd, detail=snippet))
    return out


_CAL_BLOCK = re.compile(
    r"(?is)#(\d+)\s*"
    r"Date\s*:\s*([^\n]+)\s*"
    r"Time\s*:\s*([^\n]+)\s*"
    r"Driver\s*:\s*([^\n]+)\s*"
    r"Route\s*:\s*([^\n]+)",
)


def parse_calendar_text(text: str) -> list[Trip]:
    out: list[Trip] = []
    for m in _CAL_BLOCK.finditer(text):
        num, date_line, time_line, driver_line, route_line = m.groups()
        date_line = date_line.strip()
        time_line = time_line.strip()
        driver_line = driver_line.strip()
        route_line = route_line.strip()
        try:
            # "Wednesday 01 April 2026"
            dt = datetime.strptime(date_line, "%A %d %B %Y")
        except ValueError:
            try:
                dt = datetime.strptime(date_line, "%d %B %Y")
            except ValueError:
                continue
        ymd = dt.strftime("%Y%m%d")
        try:
            hhmm = _parse_hhmm(time_line)
        except ValueError:
            continue
        nd = _norm_driver(driver_line)
        key = f"{ymd}|{hhmm}|{nd}"
        detail = f"#{num}  {route_line}"
        out.append(Trip(key=key, ymd=ymd, time_hhmm=hhmm, driver_display=nd, detail=detail))
    return out


def _multiset_match(
    calendar: list[Trip], invoice: list[Trip]
) -> tuple[list[tuple[Trip, Trip]], list[Trip], list[Trip]]:
    """Pair trips by identical key; leftovers are unmatched (each occurrence counts)."""
    inv_by_key: dict[str, list[Trip]] = defaultdict(list)
    for t in invoice:
        inv_by_key[t.key].append(t)
    matched: list[tuple[Trip, Trip]] = []
    cal_only: list[Trip] = []
    for c in calendar:
        bucket = inv_by_key.get(c.key)
        if bucket:
            i = bucket.pop(0)
            matched.append((c, i))
        else:
            cal_only.append(c)
    inv_only: list[Trip] = []
    for bucket in inv_by_key.values():
        inv_only.extend(bucket)
    return matched, cal_only, inv_only


def build_report(
    calendar_path: Path,
    invoice_path: Path,
    *,
    invoice_trip_count: int,
    matched_count: int,
    inv_not_in_calendar: list[Trip],
) -> str:
    lines: list[str] = []
    w = lines.append
    w("INVOICE vs CALENDAR (did you book everything on the invoice?)")
    w("=" * 72)
    w(f"Calendar file: {calendar_path.name}")
    w(f"Invoice file:  {invoice_path.name}")
    w("")
    w("SUMMARY")
    w("-" * 72)
    w(f"  Invoice trips found in file: {invoice_trip_count}")
    w(f"  Also found in calendar export: {matched_count}")
    w(f"  NOT found in calendar export:  {len(inv_not_in_calendar)}")
    if not inv_not_in_calendar:
        w("")
        w("  All invoice trips have a matching calendar booking (date + time + driver).")
    w("")
    w("Match rule: same calendar date, same time, same driver (name normalised).")
    w("")
    if inv_not_in_calendar:
        w("INVOICE TRIPS NOT IN YOUR CALENDAR EXPORT (book these or query the operator)")
        w("-" * 72)
        for t in inv_not_in_calendar:
            w(f"  {t.line()}")
        w("")
    w("END")
    return "\n".join(lines)


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def compare_txt_files(calendar: Path, invoice: Path, out: Path) -> int:
    cal_text = _read_text_file(calendar)
    inv_text = _read_text_file(invoice)
    cal_trips = parse_calendar_text(cal_text)
    inv_trips = parse_invoice_text(inv_text)
    matched, _cal_only, inv_only = _multiset_match(cal_trips, inv_trips)
    report = build_report(
        calendar,
        invoice,
        invoice_trip_count=len(inv_trips),
        matched_count=len(matched),
        inv_not_in_calendar=inv_only,
    )
    written = _write_report(out, report)
    print(f"OK: wrote {written.resolve()}")
    print(f"    invoice trips: {len(inv_trips)}  matched in calendar: {len(matched)}  missing from calendar: {len(inv_only)}")
    return 0


def _write_report(out: Path, report: str) -> Path:
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        return out
    except PermissionError:
        fallback = Path(os.environ.get("TEMP", ".")) / "TaxiCompare_Result.txt"
        fallback.write_text(report, encoding="utf-8")
        print(
            f"NOTE: could not write to {out} (access denied).\n"
            f"      Report saved to: {fallback.resolve()}",
            file=sys.stderr,
        )
        return fallback


def _get_program_dir() -> Path:
    """Folder where the script or bundled .exe lives (for Compare/ and output)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _default_compare_near_program(program_dir: Path) -> Path:
    """
    Prefer .\\Compare beside the .exe; if missing, use ..\\Compare when that exists
    (PyInstaller drops TaxiCompareTxt.exe in dist\\ — your real folder is Taxi\\Compare).
    """
    local = program_dir / "Compare"
    if local.is_dir():
        return local
    parent_compare = program_dir.parent / "Compare"
    if parent_compare.is_dir():
        return parent_compare
    return local


def _resolve_compare_dir(program_dir: Path) -> Path:
    """
    1) Compare_folder.txt (one line: full path) next to this program, if present and valid.
    2) Else .\\Compare beside the program, or ..\\Compare if only the parent has it
       (running from dist\\TaxiCompareTxt.exe → Taxi\\Compare).

    Typical layout: program in Taxi\\, inputs in Taxi\\Compare.
    """
    marker = program_dir / "Compare_folder.txt"
    if marker.is_file():
        for raw in marker.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            p = Path(line).expanduser()
            if not p.is_absolute():
                p = (program_dir / p).resolve()
            else:
                p = p.resolve()
            if p.is_dir():
                return p
            break
    return _default_compare_near_program(program_dir)


def _list_compare_inputs(compare_dir: Path) -> tuple[list[Path], list[Path]]:
    cals = sorted(compare_dir.glob("TaxiCalendar*.txt"))
    invs = sorted(compare_dir.glob("ABC_Invoice*.txt"))
    return cals, invs


def _default_pair(compare_dir: Path) -> tuple[Path, Path] | None:
    cals, invs = _list_compare_inputs(compare_dir)
    if len(cals) != 1 or len(invs) != 1:
        return None
    return cals[0], invs[0]


def _pick_from_list(label: str, files: list[Path]) -> Path | None:
    if not files:
        return None
    if len(files) == 1:
        return files[0]
    print(f"\n{label} — choose one:")
    for i, p in enumerate(files, 1):
        print(f"  {i}. {p.name}")
    try:
        choice = input(f"Enter number (1-{len(files)}): ").strip()
        num = int(choice)
        if 1 <= num <= len(files):
            return files[num - 1]
    except (ValueError, EOFError, OSError):
        pass
    print("Invalid choice.")
    return None


def _interactive_pair(compare_dir: Path) -> tuple[Path, Path] | None:
    cals, invs = _list_compare_inputs(compare_dir)
    if not compare_dir.is_dir():
        print(f"ERROR: folder not found: {compare_dir}")
        print("  Create a folder named Compare next to this program and put your .txt files in it.")
        return None
    if not cals:
        print(f"ERROR: no TaxiCalendar*.txt files in {compare_dir}")
        return None
    if not invs:
        print(f"ERROR: no ABC_Invoice*.txt files in {compare_dir}")
        return None
    pair = _default_pair(compare_dir)
    if pair is not None:
        return pair
    cal = _pick_from_list("Calendar export", cals)
    if cal is None:
        return None
    inv = _pick_from_list("Invoice text", invs)
    if inv is None:
        return None
    return cal, inv


def _pause_at_end(*, skip: bool = False) -> None:
    if skip:
        return
    try:
        input("\nPress Enter to exit...")
    except (EOFError, OSError):
        time.sleep(3)


def _run_standalone() -> int:
    """Double-click TaxiCompareTxt.exe — same pattern as WeeklyCircularProcessor.exe."""
    auto_run = "--all" in sys.argv or "-a" in sys.argv
    base = _get_program_dir()
    compare_dir = _resolve_compare_dir(base)
    out_path = compare_dir / "TaxiCompare_Result.txt"

    print("Taxi invoice vs calendar compare")
    print("=" * 60)
    print(f"Program folder: {base}")
    print(f"Compare folder: {compare_dir}")
    print("")

    if not compare_dir.is_dir():
        print(f"ERROR: Compare folder not found:\n  {compare_dir}")
        print("  Create a folder named Compare next to TaxiCompareTxt.exe")
        _pause_at_end(skip=auto_run)
        return 2

    cals, invs = _list_compare_inputs(compare_dir)
    if not cals:
        print("No TaxiCalendar*.txt files in Compare.")
        print("  Export from Outlook and save as TaxiCalendar_....txt in Compare\\")
        _pause_at_end(skip=auto_run)
        return 2
    if not invs:
        print("No ABC_Invoice*.txt files in Compare.")
        print("  Save the invoice as plain text ABC_Invoice_....txt in Compare\\")
        _pause_at_end(skip=auto_run)
        return 2

    pair = _default_pair(compare_dir)
    if pair is None and not auto_run:
        print("Several files found — choose which to compare:\n")
        pair = _interactive_pair(compare_dir)
        if pair is None:
            _pause_at_end()
            return 2
    elif pair is None:
        print(
            "ERROR: need exactly one TaxiCalendar*.txt and one ABC_Invoice*.txt in Compare\\"
        )
        print(f"  Found {len(cals)} calendar file(s), {len(invs)} invoice file(s).")
        _pause_at_end(skip=True)
        return 2

    cal, inv = pair
    print(f"Using calendar: {cal.name}")
    print(f"Using invoice:  {inv.name}")
    print("")

    code = compare_txt_files(cal, inv, out_path)
    if code == 0:
        print("")
        print(f"Open the report: {out_path.resolve()}")
    print("")
    print("Done.")
    _pause_at_end(skip=auto_run)
    return code


def _run_cli() -> int:
    base = _get_program_dir()
    compare_dir = _resolve_compare_dir(base)
    p = argparse.ArgumentParser(
        description="Check invoice trips against TaxiCalendar .txt; report invoice lines missing from calendar."
    )
    p.add_argument(
        "--compare-dir",
        type=Path,
        default=None,
        help="Folder containing TaxiCalendar*.txt and ABC_Invoice*.txt (overrides Compare next to exe and Compare_folder.txt)",
    )
    p.add_argument(
        "--calendar",
        type=Path,
        help="Path to TaxiCalendar_....txt (default: sole TaxiCalendar*.txt in Compare/)",
    )
    p.add_argument(
        "--invoice",
        type=Path,
        help="Path to ABC_Invoice....txt (default: sole ABC_Invoice*.txt in Compare/)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Report path (default: TaxiCompare_Result.txt inside the compare folder)",
    )
    p.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Use sole TaxiCalendar*.txt and ABC_Invoice*.txt in Compare/ (no prompts)",
    )
    args = p.parse_args()

    if args.compare_dir is not None:
        compare_dir = args.compare_dir.expanduser().resolve()

    out_path = (
        args.out.expanduser().resolve()
        if args.out is not None
        else (compare_dir / "TaxiCompare_Result.txt")
    )

    cal = args.calendar
    inv = args.invoice
    if cal is None or inv is None:
        pair = _default_pair(compare_dir)
        if pair is None:
            print(
                "ERROR: need --calendar and --invoice, or exactly one TaxiCalendar*.txt "
                f"and one ABC_Invoice*.txt in {compare_dir}",
                file=sys.stderr,
            )
            return 2
        cal, inv = pair

    if not cal.is_file():
        print(f"ERROR: calendar file not found: {cal}", file=sys.stderr)
        return 2
    if not inv.is_file():
        print(f"ERROR: invoice file not found: {inv}", file=sys.stderr)
        return 2

    return compare_txt_files(cal, inv, out_path)


def main() -> int:
    # Double-click .exe (no args), same as WeeklyCircularProcessor.
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ("--all", "-a")):
        return _run_standalone()
    return _run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
