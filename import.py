"""Small, offline Kinbor SKU importer. Python 3.10+; standard library only.

Reads *only* explicitly allowlisted product cells from the two quotation files.
Never exports EXW prices, stock, supplier barcodes, orders, or source images.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# Confirmed by the project owner. The source's separate packing-string field
# says "1/24/48" for both; the source carton-quantity cells say 112.
CONFIRMED_CARTONS = {"DTB6611-1": 112, "DTB6616-1": 112}

COLUMNS = [
    "sku", "name_zh", "collection", "category", "size_hint", "packing_raw",
    "units_per_carton", "moq_cartons", "moq_units", "carton_qty_basis",
    "source_sheet", "source_row",
]


def _read_shared_strings(z: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(NS + "t"))
            for si in root.findall(NS + "si")]


def _first_visible_sheet(z: ZipFile) -> tuple[str, str]:
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = workbook.find(NS + "sheets")
    visible = [s for s in sheets if s.get("state", "visible") == "visible"]
    if not visible:
        raise ValueError("Workbook has no visible worksheet")
    sheet = visible[0]
    relationships = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): r.get("Target", "") for r in relationships}
    target = targets[sheet.get(REL + "id")]
    if target.startswith("/"):
        part = target.lstrip("/")
    else:
        from posixpath import normpath
        part = normpath("xl/" + target)
    if not part.startswith("xl/worksheets/") or part not in z.namelist():
        raise ValueError("Unexpected worksheet location")
    return sheet.get("name", ""), part


def _read_sheet(path: Path) -> tuple[str, dict[int, dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with ZipFile(path) as z:
        sheet_name, part = _first_visible_sheet(z)
        shared = _read_shared_strings(z)
        root = ET.fromstring(z.read(part))
        rows: dict[int, dict[str, str]] = {}
        for row in root.iter(NS + "row"):
            data = {}
            for cell in row.findall(NS + "c"):
                col = re.match(r"[A-Z]+", cell.get("r", ""))
                if not col or cell.find(NS + "f") is not None:
                    continue  # Do not execute or export formulas.
                value = cell.find(NS + "v")
                if cell.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.iter(NS + "t"))
                elif value is None:
                    continue
                elif cell.get("t") == "s":
                    text = shared[int(value.text)]
                else:
                    text = value.text or ""
                data[col.group()] = text.strip()
            if data:
                rows[int(row.get("r"))] = data
        return sheet_name, rows


def _positive_int(value: str, context: str) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"Missing or invalid carton quantity at {context}: {value!r}")
    n = int(value)
    if n <= 0:
        raise ValueError(f"Nonpositive carton quantity at {context}")
    return n


def _category(name: str) -> str:
    """Broad, *inferred* grouping for retailer search, not a supplier fact."""
    groups = [
        ("Refills & Inserts", r"内芯|活页内页|活页插板"),
        ("Sticky Notes & Page Flags", r"便签|自粘|索引标记|标记贴"),
        ("Stickers & Decorative Tape", r"贴纸|刺绣贴|磁吸贴贴"),
        ("Pouches & Cases", r"笔袋|化妆包|零钱包|耳机包|耳机零钱包|收纳包|卡套|拉链包|手提包|编织袋"),
        ("Pens & Writing", r"中性笔|马克笔|钢笔"),
        ("Desk & Office Tools", r"固体胶|套尺|直尺|转转尺|卷尺|手腕垫"),
        ("Planners & Calendars", r"周计划|三年计划|五年计划|时间轴|年历|日历"),
        ("Notebooks & Journals", r"手帐|手账|口袋本|硬面本|软面本|线圈本|横线本|方格本|索引本|阅读套装|DIY素材本|答案之书|B6本|A5本|笔记本|本套装|本1|本2|哈哈镜本|八分格"),
        ("Mugs & Drinkware", r"马克杯|水杯"),
        ("Gifts & Lifestyle", r"毛绒|盲盒|公仔|挂件|钥匙扣|冰箱贴|抱枕|拖鞋|发夹|帽|擦手巾|支架|卡套|玩偶|挂钩|拓展扣|商务套装|文具套装|fu鸭"),
    ]
    for label, pattern in groups:
        if re.search(pattern, name, flags=re.IGNORECASE):
            return label
    return "Other / Review"


def _safe_text(value: str) -> str:
    """Prevent text fields being interpreted as spreadsheet formulas in CSV readers."""
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _rows_for(path: Path, kind: str) -> list[dict[str, str | int]]:
    sheet, rows = _read_sheet(path)
    if kind == "original":
        if sheet != "原创-在售产品" or rows.get(2, {}).get("B") != "产品货号":
            raise ValueError("Unexpected original-design workbook layout")
        collection, start, qty_col = "Original Design", 3, "F"
    else:
        if sheet != "Brunch Brother新品" or "货号" not in rows.get(3, {}).get("B", ""):
            raise ValueError("Unexpected Brunch Brother workbook layout")
        collection, start, qty_col = "Brunch Brother", 5, "I"
    output = []
    for row_num, fields in sorted(rows.items()):
        if row_num < start:
            continue
        sku = fields.get("B", "")
        if not sku or sku in {"合计", "Total", "TOTAL"}:
            continue
        if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", sku):
            raise ValueError(f"Invalid SKU in {sheet}!B{row_num}: {sku!r}")
        name = fields.get("C", "")
        if not name:
            raise ValueError(f"Missing product name for {sku}")
        raw_qty = _positive_int(fields.get(qty_col, ""), f"{sheet}!{qty_col}{row_num}")
        if kind == "original":
            raw_packing = fields.get("E", "")
            pack_last = raw_packing.split("/")[-1].strip()
            if pack_last and pack_last.isdigit() and int(pack_last) != raw_qty and sku not in CONFIRMED_CARTONS:
                raise ValueError(f"Packaging/carton conflict needs review: {sku}")
        else:
            raw_packing = f"unit={fields.get('F', '?')}; inner={fields.get('G', '?')}; master={fields.get('H', '?')}"
            master = fields.get("H", "")
            if master.isdigit() and int(master) != raw_qty:
                raise ValueError(f"Master/carton conflict needs review: {sku}")
        qty = CONFIRMED_CARTONS.get(sku, raw_qty)
        size_match = re.search(r"(?i)(?<![a-z0-9])(A5|A6|A7|B5|B6|M5|mini)", name)
        record: dict[str, str | int] = {
            "sku": sku,
            "name_zh": _safe_text(name),
            "collection": collection,
            "category": _category(name),
            "size_hint": size_match.group(1).upper() if size_match else "",
            "packing_raw": _safe_text(raw_packing),
            "units_per_carton": qty,
            "moq_cartons": 1,
            "moq_units": qty,
            "carton_qty_basis": "user_confirmed" if sku in CONFIRMED_CARTONS else "source",
            "source_sheet": sheet,
            "source_row": row_num,
        }
        output.append(record)
    return output


def import_catalog(original: Path, brunch: Path) -> list[dict[str, str | int]]:
    """Allowlists product fields; refuses unexpected row counts or duplicate SKUs."""
    products = _rows_for(original, "original") + _rows_for(brunch, "brunch")
    counts = Counter(p["collection"] for p in products)
    if counts != {"Original Design": 120, "Brunch Brother": 90}:
        raise ValueError(f"Unexpected catalog sizes (source may have changed): {counts}")
    skus = [str(p["sku"]) for p in products]
    if len(skus) != len(set(skus)):
        raise ValueError("Duplicate SKU across source workbooks")
    if set(CONFIRMED_CARTONS) - set(skus):
        raise ValueError("Confirmed carton SKUs missing from source")
    return products


def write_catalog(records: list[dict[str, str | int]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically to avoid partial catalog after an interrupted run.
    tmp = output.with_name(output.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        writer.writerows({k: _safe_text(v) if isinstance(v, str) else v
                          for k, v in row.items()} for row in records)
    tmp.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a safe public Kinbor product catalog from two original XLSX files")
    parser.add_argument("--original", required=True, type=Path, help="Kinbor Original Design XLSX")
    parser.add_argument("--brunch", required=True, type=Path, help="Kinbor x Brunch Brother XLSX")
    parser.add_argument("--output", type=Path, default=Path("products.csv"))
    args = parser.parse_args()
    try:
        rows = import_catalog(args.original, args.brunch)
        write_catalog(rows, args.output)
    except (ValueError, FileNotFoundError, KeyError, IndexError, OSError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")
    counts = Counter(row["collection"] for row in rows)
    print(f"Wrote {len(rows)} real SKUs to {args.output} ({dict(counts)}). No price or stock fields exported.")


if __name__ == "__main__":
    main()
