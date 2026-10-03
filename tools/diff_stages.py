#!/usr/bin/env python3
"""Diff the deliverables between two output folders (used for the email replies
and changes_report.md). Usage: python3 tools/diff_stages.py <old dir> <new dir>"""
import csv, json, re, sys, os


def rows(path, key):
    with open(path, newline="", encoding="utf-8") as f:
        return {r[key]: r for r in csv.DictReader(f)}


def lib(d):
    h = open(os.path.join(d, "coa_library.html"), encoding="utf-8").read()
    return re.findall(r'<tr data-sku="([^"]+)"', h)


def featured(d):
    t = open(os.path.join(d, "featured_products.md"), encoding="utf-8").read()
    return re.findall(r"^\| \d \| (P\d\d) \|", t, re.M)


def email_total(d):
    t = open(os.path.join(d, "client_email.md"), encoding="utf-8").read()
    m = re.search(r"\*\*(\d+) draft products, total value USD ([\d,.]+)\*\*", t)
    return m.group(1), m.group(2)


def diff(a, b):
    out = []
    ia, ib = rows(os.path.join(a, "woocommerce_import.csv"), "SKU"), rows(os.path.join(b, "woocommerce_import.csv"), "SKU")
    out.append("## woocommerce_import.csv field changes")
    for sku in ia:
        for col in ia[sku]:
            if ia[sku][col] != ib[sku][col]:
                out.append(f"- {sku} {ia[sku]['Name']}: {col}: '{ia[sku][col]}' -> '{ib[sku][col]}'")
    fa, fb = json.load(open(os.path.join(a, "coa_feed.json"))), json.load(open(os.path.join(b, "coa_feed.json")))
    la, lb = lib(a), lib(b)
    out.append("## library / feed")
    out.append(f"- teaser: '{fa['teaser']['text']}' -> '{fb['teaser']['text']}'")
    out.append(f"- added: {[s for s in lb if s not in la]}; removed: {[s for s in la if s not in lb]}")
    out.append(f"- order old: {','.join(la)}")
    out.append(f"- order new: {','.join(lb)}")
    ra, rb = rows(os.path.join(a, "retest_schedule.csv"), "SKU"), rows(os.path.join(b, "retest_schedule.csv"), "SKU")
    out.append("## retest_schedule.csv")
    out.append(f"- rows {len(ra)} -> {len(rb)}; added {[s for s in rb if s not in ra]}; removed {[s for s in ra if s not in rb]}")
    shift = {int(rb[s]['days_remaining']) - int(ra[s]['days_remaining']) for s in ra if s in rb}
    out.append(f"- days_remaining shift for existing rows: {sorted(shift)}")
    for s in rb:
        if s in ra and ra[s]["due_soon"] != rb[s]["due_soon"]:
            out.append(f"- {s} due_soon {ra[s]['due_soon']} -> {rb[s]['due_soon']} (days {ra[s]['days_remaining']} -> {rb[s]['days_remaining']})")
        if s in ra and (ra[s]["test_date"], ra[s]["retest_due"]) != (rb[s]["test_date"], rb[s]["retest_due"]):
            out.append(f"- {s} dates changed {ra[s]['test_date']}/{ra[s]['retest_due']} -> {rb[s]['test_date']}/{rb[s]['retest_due']}")
    out.append(f"- due_soon=yes old: {[s for s in ra if ra[s]['due_soon']=='yes']} new: {[s for s in rb if rb[s]['due_soon']=='yes']}")
    out.append("## featured")
    out.append(f"- {featured(a)} -> {featured(b)}")
    out.append("## scorecard")
    sa, sb = rows(os.path.join(a, "supplier_scorecard.csv"), "lab"), rows(os.path.join(b, "supplier_scorecard.csv"), "lab")
    for lab in sa:
        for c in sa[lab]:
            if sa[lab][c] != sb[lab][c]:
                out.append(f"- {lab}: {c} {sa[lab][c]} -> {sb[lab][c]}")
    out.append("## price changes")
    pa, pb = rows(os.path.join(a, "price_changes.csv"), "SKU"), rows(os.path.join(b, "price_changes.csv"), "SKU")
    out.append(f"- {sorted(pa)} -> {sorted(pb)}" + ("" if pa == pb else " (CHANGED)"))
    out.append("## client email totals")
    out.append(f"- {email_total(a)} -> {email_total(b)}")
    return "\n".join(out)


if __name__ == "__main__":
    print(diff(sys.argv[1], sys.argv[2]))
