#!/usr/bin/env python3
"""Build the COA deliverables from the transcribed COA lines, the product
sheet, the price list and the store rules (rules.md, v3).

Usage:  python3 tools/build.py phase1
        python3 tools/build.py final      (applies inbox emails 01-03)
        python3 tools/build.py after1|after2   (intermediate states, for checks)

All COA values come from tools/coa_raw.csv, a line-by-line transcription of the
PDFs in coa/ (and, for the final build, inbox/ attachments).
"""
import csv, json, sys, os, re, html, copy
from datetime import date
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = date(2026, 9, 30)
CUTOFF = date(2025, 9, 30)
URL_BASE = "https://example-store.test/coa/"
BATCH_RE = re.compile(r"^PP-\d{4}-\d{3}$")

LAB_CODE = {"MAL": "Meridian Analytical Labs", "NPT": "Northgate Peptide Testing",
            "CBA": "Coastal BioAssay"}
LAB_ORDER = ["Meridian Analytical Labs", "Northgate Peptide Testing", "Coastal BioAssay"]

# Lab names -> product-sheet names (rule 2: synonyms, spacing, extra words).
SYNONYMS = {
    "bpc-157": "BPC-157", "bpc 157": "BPC-157",
    "thymosin beta-4 fragment (tb-500)": "TB-500", "tb-500": "TB-500",
    "ghk-cu": "GHK-Cu", "ipamorelin": "Ipamorelin",
    "cjc-1295 dac": "CJC-1295 (with DAC)",
    "sermorelin": "Sermorelin", "tesamorelin": "Tesamorelin",
    "semaglutide": "Semaglutide", "tirzepatide": "Tirzepatide",
    "retatrutide": "Retatrutide", "aod-9604": "AOD-9604",
    "epitalon (epithalon)": "Epitalon", "selank": "Selank", "semax": "Semax",
    "bremelanotide (pt-141)": "PT-141", "dsip": "DSIP",
    "kisspeptin-10": "Kisspeptin-10", "mots-c": "MOTS-c",
    "thymalfasin (thymosin alpha-1)": "Thymosin Alpha-1", "ll-37": "LL-37",
    "hexarelin": "Hexarelin", "ghrp-2 (pralmorelin)": "GHRP-2", "ghrp-6": "GHRP-6",
    "oxytocin": "Oxytocin", "kpv": "KPV", "cagrilintide": "Cagrilintide",
    "melanotan ii (mt-2)": "Melanotan II",
    "gonadorelin acetate (gnrh)": "Gonadorelin",
}
# Names that are ambiguous on their own; resolved by theoretical mass.
MASS_RESOLVED = {"cjc-1295": {3367.9: "CJC-1295 (no DAC)", 3647.2: "CJC-1295 (with DAC)"}}

REASONS = ["no COA", "conflicting COAs", "missing field", "size conflict",
           "purity below 98.0", "identity failed", "COA older than 12 months"]
ACTIONS = {
    "no COA": "send a COA",
    "conflicting COAs": "confirm which report is correct",
    "missing field": "send a COA showing the missing {field}",
    "size conflict": "confirm the size and add a price for it",
    "purity below 98.0": "retest or replace the batch",
    "identity failed": "repeat the mass-spec identity test",
    "COA older than 12 months": "send a COA tested within the last 12 months",
}
FIELD_LABEL = {"batch": "batch number", "test_date": "test date", "purity": "purity",
               "size": "declared amount (size)"}


# ---------------------------------------------------------------- loading
def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def iso_date(raw, lab):
    raw = raw.strip()
    if not raw:
        return None
    if lab == "Meridian Analytical Labs":
        y, m, d = raw.split("-")
    elif lab == "Northgate Peptide Testing":
        d, m, y = raw.split(".")
    else:
        m, d, y = raw.split("/")
    return date(int(y), int(m), int(d))


def num(raw):
    raw = raw.replace("%", "").replace("Da", "").replace(",", ".").strip()
    return float(raw) if raw else None


def to_mg(raw):
    raw = raw.strip()
    if not raw:
        return None
    if raw.endswith(" g"):
        return int(round(float(raw[:-2].replace(",", ".")) * 1000))
    return int(round(float(raw.replace("mg", "").strip())))


def load_lines(extra_raw=None, void_extra=None):
    rows = read_csv(os.path.join(ROOT, "tools", "coa_raw.csv"))
    if extra_raw:
        rows += read_csv(extra_raw)
    lines, seen = [], defaultdict(int)
    for r in rows:
        seen[r["pdf_file"]] += 1
        ln = dict(r)
        ln["line_no"] = seen[r["pdf_file"]]
        ln["date"] = iso_date(r["date_printed"], r["lab"])
        ln["mg"] = to_mg(r["amount_printed"])
        ln["purity"] = num(r["purity_printed"])
        ln["theo"] = num(r["theo_printed"])
        ln["obs"] = num(r["obs_printed"])
        if void_extra and r["pdf_file"] in void_extra:
            ln["remark"] = "; ".join(x for x in [r["remark"], void_extra[r["pdf_file"]]] if x)
        ln["void"] = "VOID" in ln["remark"]
        m = re.search(r"supersedes report (\S+)", r["remark"])
        ln["supersedes"] = m.group(1) + ".pdf" if m else None
        lines.append(ln)
    return lines


# ---------------------------------------------------------------- matching
def match_lines(lines, products):
    by_name = defaultdict(list)
    for p in products:
        by_name[p["Product"]].append(p)
    for ln in lines:
        key = ln["product_as_printed"].strip().lower()
        name = SYNONYMS.get(key)
        how = []
        if name is None and key in MASS_RESOLVED:
            name = MASS_RESOLVED[key].get(ln["theo"])
            if name:
                how.append(f"name '{ln['product_as_printed']}' alone is ambiguous; theoretical mass "
                           f"{ln['theo']} Da identifies {name}")
        if name is None:
            ln["sku"] = ""
            ln["match_reason"] = (f"no product in products.csv is '{ln['product_as_printed']}' "
                                  f"(theoretical mass {ln['theo']} Da)")
            continue
        cands = by_name.get(name, [])
        exact = [p for p in cands if int(p["Size_mg"]) == ln["mg"]]
        if exact:
            p = exact[0]
            if not how:
                how.append(f"name '{ln['product_as_printed']}' = {name}")
            how.append(f"declared {ln['mg']} mg = sheet size")
        elif len(cands) == 1:
            p = cands[0]
            if not how:
                how.append(f"name '{ln['product_as_printed']}' = {name}")
            how.append(f"declared {ln['mg']} mg differs from "
                       f"sheet size {p['Size_mg']} mg (only {name} SKU, size handled by rule 8)")
        else:
            ln["sku"] = ""
            ln["match_reason"] = f"{name} {ln['mg']} mg is not a sheet size"
            continue
        if ln["theo"] is not None:
            how.append(f"theoretical mass {ln['theo']} Da")
        ln["sku"] = p["SKU"]
        ln["match_reason"] = "; ".join(how)
    # mass consistency: every line matched to the same peptide name should share a theoretical mass
    masses = defaultdict(set)
    for ln in lines:
        if ln["sku"]:
            masses[next(p["Product"] for p in products if p["SKU"] == ln["sku"])].add(ln["theo"])
    return masses


# ---------------------------------------------------------------- decisions
def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, d.day)


def fmt_p(x):
    return "" if x is None else f"{x:.1f}"


def decide(products, prices, lines):
    price_of = {(r["Product"], int(r["Size_mg"])): r["Price_USD"] for r in prices}
    superseded = {ln["supersedes"] for ln in lines if ln["supersedes"]}
    out = OrderedDict()
    for p in products:
        sku = p["SKU"]
        mine = [ln for ln in lines if ln["sku"] == sku]
        d = {"sku": sku, "name": p["Product"], "sheet": p, "all_lines": mine,
             "ignored": [], "notes": [], "from_sheet": [], "chosen": None}
        usable = []
        for ln in mine:
            if ln["void"]:
                d["ignored"].append((ln, ("withdrawn by the lab, treated as VOID per email 01 (rule 3)"
                                          if "withdrawn" in ln["remark"] else "stamped VOID (rule 3)")))
            elif ln["pdf_file"] in superseded:
                sup = next(x for x in lines if x["supersedes"] == ln["pdf_file"])
                d["ignored"].append((ln, f"superseded by revision {sup['pdf_file']} (rule 4)"))
            else:
                usable.append(ln)
        # group by batch (rule 4)
        groups = defaultdict(list)
        for ln in usable:
            groups[ln["batch"] or ("<blank>" + ln["pdf_file"])].append(ln)
        cands = []
        for b, g in groups.items():
            conflict = len(g) > 1 and len({(x["purity"], x["mg"], x["theo"], x["obs"]) for x in g}) > 1
            gdate = max((x["date"] for x in g if x["date"]), default=None)
            cands.append({"batch": b, "lines": g, "conflict": conflict, "date": gdate})
        sheet_size = int(p["Size_mg"])
        sheet_price = p["Price_USD"]
        list_price = price_of.get((p["Product"], sheet_size))
        d["list_price_sheet_size"] = list_price
        reason = None
        vals = {"batch": "", "test_date": None, "purity": None, "size": None}
        coa_pdf = ""
        price = sheet_price
        price_reason = ""
        size_status = None
        if not cands:
            reason = "no COA"
            if list_price and list_price != sheet_price:
                price, price_reason = list_price, "price list differs from sheet price (rule 8)"
        else:
            cands.sort(key=lambda c: (c["date"] or date.min), reverse=True)
            best = cands[0]
            for c in cands[1:]:
                for ln in c["lines"]:
                    d["ignored"].append((ln, f"older batch than chosen {best['batch']} (rule 5)"))
            if best["conflict"]:
                reason = "conflicting COAs"
                vals["batch"] = best["batch"]
                d["conflict_lines"] = best["lines"]
                if list_price and list_price != sheet_price:
                    price, price_reason = list_price, "price list differs from sheet price (rule 8)"
            else:
                ch = best["lines"][0]
                for ln in best["lines"][1:]:
                    d["ignored"].append((ln, f"duplicate report of batch {best['batch']} agreeing with {ch['pdf_file']}"))
                d["chosen"] = ch
                coa_pdf = ch["pdf_file"]
                vals["batch"] = ch["batch"]
                vals["test_date"] = ch["date"]
                vals["purity"] = ch["purity"]
                vals["size"] = ch["mg"]
                sheet_vals = {"batch": p["Batch_Listed"] or "",
                              "test_date": date.fromisoformat(p["Test_Date_Listed"]) if p["Test_Date_Listed"] else None,
                              "purity": float(p["Purity_Listed_pct"]) if p["Purity_Listed_pct"] else None,
                              "size": sheet_size}
                missing = []
                for f in ["batch", "test_date", "purity", "size"]:
                    if vals[f] in (None, ""):
                        if sheet_vals[f] not in (None, ""):
                            vals[f] = sheet_vals[f]
                            d["from_sheet"].append(f)
                        else:
                            missing.append(f)
                d["missing"] = missing
                # price / size (rule 8)
                if vals["size"] is not None and vals["size"] != sheet_size:
                    alt = price_of.get((p["Product"], vals["size"]))
                    if alt:
                        size_status = "size corrected"
                        price = alt
                        price_reason = (f"size corrected: COA declares {vals['size']} mg, sheet {sheet_size} mg; "
                                        f"price list row {p['Product']} {vals['size']} mg (rule 8)")
                    else:
                        size_status = "size conflict"
                        price = sheet_price
                else:
                    if list_price and list_price != sheet_price:
                        price, price_reason = list_price, "price list differs from sheet price (rule 8)"
                # status (rule 9)
                if missing:
                    reason = "missing field"
                elif size_status == "size conflict":
                    reason = "size conflict"
                elif vals["purity"] < 98.0:
                    reason = "purity below 98.0"
                elif ch["theo"] is None or ch["obs"] is None or abs(ch["obs"] - ch["theo"]) > 1.0 + 1e-9:
                    reason = "identity failed"
                elif vals["test_date"] < CUTOFF:
                    reason = "COA older than 12 months"
                else:
                    reason = "ok"
        d["reason"] = reason
        d["status"] = "publish" if reason == "ok" else "draft"
        d["vals"] = vals
        d["coa_pdf"] = coa_pdf
        d["price"] = price
        d["price_reason"] = price_reason
        d["size_status"] = size_status
        d["url"] = (URL_BASE + f"{sku.lower()}-{vals['batch'].lower()}/") if vals["batch"] else ""
        out[sku] = d
    return out


# ---------------------------------------------------------------- state / emails
def base_state():
    return {
        "products": read_csv(os.path.join(ROOT, "products.csv")),
        "prices": read_csv(os.path.join(ROOT, "price_list.csv")),
        "extra_raw": None,
        "pdf_dirs": {},          # pdf_file -> folder relative to project root (default coa/)
        "void_extra": {},        # pdf_file -> reason (reports voided by the client after delivery)
        "ref": date(2026, 9, 30),
        "cutoff": date(2025, 9, 30),
        "events": [],
    }


def apply_email(state, n):
    """Client follow-ups; see inbox/email_0N.md. Filled in Part 3."""
    import email_changes
    email_changes.apply(state, n)


# ---------------------------------------------------------------- outputs
def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def build(phase):
    state = base_state()
    n_emails = {"phase1": 0, "after1": 1, "after2": 2, "final": 3}[phase]
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    for i in range(1, n_emails + 1):
        apply_email(state, i)
    global REF, CUTOFF
    REF, CUTOFF = state["ref"], state["cutoff"]
    products, prices = state["products"], state["prices"]
    lines = load_lines(state["extra_raw"], state["void_extra"])
    masses = match_lines(lines, products)
    dec = decide(products, prices, lines)
    outdir = os.path.join(ROOT, "output", {"phase1": "phase1", "final": "final"}.get(phase, os.path.join("steps", phase)))
    os.makedirs(outdir, exist_ok=True)
    pdf_dir = lambda f: state["pdf_dirs"].get(f, "coa")
    ctx = {"state": state, "lines": lines, "dec": dec, "masses": masses, "pdf_dir": pdf_dir,
           "outdir": outdir, "phase": phase}

    # chosen-line markers for coa_extracted
    used = {}
    for d in dec.values():
        if d["chosen"]:
            used[(d["chosen"]["pdf_file"], d["chosen"]["line_no"])] = d
    ign = {}
    for d in dec.values():
        for ln, why in d["ignored"]:
            ign[(ln["pdf_file"], ln["line_no"])] = why
        for ln in d.get("conflict_lines", []):
            others = ", ".join(x["pdf_file"] for x in d["conflict_lines"] if x is not ln)
            ign[(ln["pdf_file"], ln["line_no"])] = (f"not used: same batch {ln['batch']} as {others} with different "
                                                    f"purity/mass and no revision note -> product held as conflicting COAs (rule 4)")
    ctx["used"], ctx["ign"] = used, ign

    # coa_extracted.csv
    rows = []
    for ln in lines:
        k = (ln["pdf_file"], ln["line_no"])
        if k in used:
            st = f"USED as final COA for {ln['sku']}"
            if used[k]["status"] == "draft":
                st += f" (product draft: {used[k]['reason']})"
        elif k in ign:
            st = "IGNORED: " + ign[k]
        elif not ln["sku"]:
            st = "IGNORED: matches no product (rule 2) - " + ln["match_reason"]
        else:
            st = "IGNORED"
        note = "; ".join(x for x in [ln["remark"], st] if x)
        rows.append([ln["pdf_file"], ln["lab"], ln["product_as_printed"], ln["sku"], ln["mg"] if ln["mg"] is not None else "",
                     ln["batch"], ln["date"].isoformat() if ln["date"] else "", fmt_p(ln["purity"]),
                     ln["theo"] if ln["theo"] is not None else "", ln["obs"] if ln["obs"] is not None else "", note])
    write_csv(os.path.join(outdir, "coa_extracted.csv"),
              ["pdf_file", "lab", "product_as_printed", "matched_sku", "declared_amount_mg", "batch", "test_date",
               "purity", "theoretical_mass", "observed_mass", "notes"], rows)

    # woocommerce_import.csv
    rows = []
    for d in dec.values():
        v = d["vals"]
        if d["reason"] in ("no COA",):
            r = ["", "", "", "", "", ""]
        elif d["reason"] == "conflicting COAs":
            r = [v["batch"], "", "", "", "", d["url"]]
        else:
            r = [v["batch"], v["test_date"].isoformat() if v["test_date"] else "", fmt_p(v["purity"]),
                 v["size"] if v["size"] is not None else "", d["coa_pdf"], d["url"]]
        rows.append([d["sku"], d["name"], d["price"], d["status"]] + r + [d["reason"]])
    write_csv(os.path.join(outdir, "woocommerce_import.csv"),
              ["SKU", "Name", "Regular price", "Status", "coa_batch", "coa_test_date", "coa_purity", "coa_size_mg",
               "coa_pdf", "coa_url", "status_reason"], rows)

    # price_changes.csv
    rows = [[d["sku"], d["name"], d["sheet"]["Price_USD"], d["price"], d["price_reason"]]
            for d in dec.values() if d["price"] != d["sheet"]["Price_USD"]]
    write_csv(os.path.join(outdir, "price_changes.csv"), ["SKU", "Name", "old_price", "new_price", "reason"], rows)
    ctx["price_changes"] = rows

    # library / feed
    pub = [d for d in dec.values() if d["status"] == "publish"]
    pub.sort(key=lambda d: d["sku"])
    pub.sort(key=lambda d: d["vals"]["test_date"], reverse=True)
    n = len(pub)
    mean = round(sum(d["vals"]["purity"] for d in pub) / n + 1e-12, 2) if n else 0.0
    teaser = f"{n} verified COAs · average purity {mean:.2f} %"
    ctx.update(pub=pub, mean=mean, teaser=teaser)
    write_library(ctx)
    feed = {"teaser": {"text": teaser, "verified_coas": n, "average_purity": float(f"{mean:.2f}")},
            "reference_date": REF.isoformat(),
            "products": [{"sku": d["sku"], "product": d["name"], "batch": d["vals"]["batch"],
                          "test_date": d["vals"]["test_date"].isoformat(), "purity": float(fmt_p(d["vals"]["purity"])),
                          "coa_pdf": f"{pdf_dir(d['coa_pdf'])}/{d['coa_pdf']}", "coa_url": d["url"]} for d in pub]}
    with open(os.path.join(outdir, "coa_feed.json"), "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # retest schedule: every product whose final test date is known (published and draft)
    sched = []
    for d in dec.values():
        td = d["vals"]["test_date"] if d["reason"] not in ("no COA", "conflicting COAs") else None
        if td:
            due = add_months(td, 12)
            days = (due - REF).days
            sched.append((due, d["sku"], d["name"], td, days, "yes" if days <= 60 else "no", d))
    sched.sort(key=lambda x: (x[0], x[1]))
    write_csv(os.path.join(outdir, "retest_schedule.csv"),
              ["SKU", "Name", "test_date", "retest_due", "days_remaining", "due_soon"],
              [[s[1], s[2], s[3].isoformat(), s[0].isoformat(), s[4], s[5]] for s in sched])
    due_soon = {s[1]: s[5] for s in sched}
    ctx["sched"], ctx["due_soon"] = sched, due_soon

    # featured
    cand = [d for d in pub if due_soon.get(d["sku"]) == "no"]
    cand.sort(key=lambda d: d["sku"])
    cand.sort(key=lambda d: d["vals"]["test_date"], reverse=True)
    cand.sort(key=lambda d: d["vals"]["purity"], reverse=True)
    feat = cand[:3]
    ctx["featured"] = feat
    write_featured(ctx)

    # scorecard
    sc = []
    labs = LAB_ORDER
    for lab in labs:
        ll = [ln for ln in lines if ln["lab"] == lab]
        pdfs = sorted({ln["pdf_file"] for ln in ll})
        u = [ln for ln in ll if (ln["pdf_file"], ln["line_no"]) in used]
        voids = sorted({ln["pdf_file"] for ln in ll if ln["void"]})
        ubd = [ln for ln in u if used[(ln["pdf_file"], ln["line_no"])]["status"] == "draft"]
        pur = [ln["purity"] for ln in u if ln["purity"] is not None]
        mp = f"{round(sum(pur) / len(pur) + 1e-12, 2):.2f}" if pur else ""
        sc.append([lab, len(pdfs), len(ll), len(u), len(ll) - len(u), len(voids), len(ubd), mp])
    write_csv(os.path.join(outdir, "supplier_scorecard.csv"),
              ["lab", "pdfs_received", "results_listed", "results_used", "results_ignored", "void_reports",
               "used_but_draft", "mean_purity_used"], sc)
    ctx["scorecard"] = sc

    write_exceptions(ctx)
    write_client_email(ctx)
    write_reading_notes(ctx)
    return ctx


def esc(s):
    return html.escape(str(s))


def write_library(ctx):
    rows = []
    for d in ctx["pub"]:
        v = d["vals"]
        href = f"../../{ctx['pdf_dir'](d['coa_pdf'])}/{d['coa_pdf']}"
        rows.append(f'      <tr data-sku="{esc(d["sku"])}"><td>{esc(d["name"])}</td><td>{esc(v["batch"])}</td>'
                    f'<td>{v["test_date"].isoformat()}</td><td>{fmt_p(v["purity"])} %</td>'
                    f'<td><a href="{esc(href)}">{esc(d["coa_pdf"])}</a></td></tr>')
    body = "\n".join(rows)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COA Library</title>
<style>
  :root {{ --bg:#fff; --fg:#1d232a; --muted:#5b6672; --line:#dde2e7; --accent:#0b6e4f; --tint:#eef6f2; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#14181c; --fg:#e7ecef; --muted:#9aa6b1; --line:#2b3339; --accent:#5fd0a3; --tint:#1b2a24; }} }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
  main {{ max-width:960px; margin:0 auto; padding:24px 16px; }}
  .teaser {{ background:var(--tint); color:var(--accent); font-weight:600; padding:12px 16px; border-radius:8px; }}
  h1 {{ font-size:1.5rem; margin:20px 0 4px; }}
  p.note {{ color:var(--muted); margin:0 0 16px; }}
  .wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }}
  th {{ color:var(--muted); font-weight:600; font-size:.85rem; text-transform:uppercase; letter-spacing:.03em; }}
  td:nth-child(4) {{ font-variant-numeric:tabular-nums; }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<main>
  <div class="teaser" id="coa-teaser">{esc(ctx['teaser'])}</div>
  <h1>Certificate of Analysis library</h1>
  <p class="note">Published products only, newest test date first (ties by SKU). Reference date {REF.isoformat()}.</p>
  <div class="wrap">
  <table id="coa-library">
    <thead><tr><th>Product</th><th>Batch</th><th>Test date</th><th>Purity</th><th>COA PDF</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  </div>
</main>
</body>
</html>
"""
    with open(os.path.join(ctx["outdir"], "coa_library.html"), "w", encoding="utf-8") as f:
        f.write(page)


def write_featured(ctx):
    pub_sorted = sorted([d for d in ctx["pub"]], key=lambda d: (-d["vals"]["purity"], d["sku"]))
    excluded = [d for d in pub_sorted if ctx["due_soon"].get(d["sku"]) == "yes"]
    out = ["# Featured products", "",
           f"Rule 14: the 3 published products with the highest purity, excluding any with due_soon = yes "
           f"(reference date {REF.isoformat()}); ties by newer test date, then lower SKU.", ""]
    if excluded:
        out.append("Excluded because their retest is due within 60 days: " +
                   ", ".join(f"{d['sku']} {d['name']} ({fmt_p(d['vals']['purity'])} %)" for d in excluded) + ".")
        out.append("")
    out += ["| # | SKU | Name | Purity | Test date |", "|---|---|---|---|---|"]
    for i, d in enumerate(ctx["featured"], 1):
        out.append(f"| {i} | {d['sku']} | {d['name']} | {fmt_p(d['vals']['purity'])} % | {d['vals']['test_date'].isoformat()} |")
    out.append("")
    pool = [d for d in ctx["pub"] if ctx["due_soon"].get(d["sku"]) == "no"]
    pool.sort(key=lambda d: d["sku"])
    pool.sort(key=lambda d: d["vals"]["test_date"], reverse=True)
    pool.sort(key=lambda d: d["vals"]["purity"], reverse=True)
    for i, d in enumerate(ctx["featured"], 1):
        p = d["vals"]["purity"]
        same = [x for x in pool if x["vals"]["purity"] == p and x is not d]
        rank = ["highest", "second-highest", "third-highest"][i - 1]
        why = (f"{d['sku']} {d['name']} has the {rank} purity ({fmt_p(p)} %) among published products that are not due for retest"
               f" (retest due {add_months(d['vals']['test_date'], 12).isoformat()})")
        if same:
            later = [x for x in same if pool.index(x) > pool.index(d)]
            if later:
                why += (f", and wins the tie with " + ", ".join(x["sku"] for x in later) +
                        " on " + ("newer test date" if any(x["vals"]["test_date"] != d["vals"]["test_date"] for x in later) else "lower SKU"))
        out.append(f"- **{d['sku']}**: {why}.")
    if len(pool) > 3:
        nxt = pool[3]
        out += ["", f"Next in line: {nxt['sku']} {nxt['name']} ({fmt_p(nxt['vals']['purity'])} %, tested {nxt['vals']['test_date'].isoformat()})."]
    with open(os.path.join(ctx["outdir"], "featured_products.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def reason_detail(d):
    v, ch = d["vals"], d["chosen"]
    r = d["reason"]
    if r == "no COA":
        return "No COA in coa/ matches this product (name, amount and mass)."
    if r == "conflicting COAs":
        parts = [f"{x['pdf_file']} ({x['lab']}, tested {x['date']}, purity {fmt_p(x['purity'])} %, "
                 f"mass {x['theo']}/{x['obs']} Da)" for x in d["conflict_lines"]]
        return f"Batch {v['batch']} has two reports that disagree and neither says it supersedes the other: " + "; ".join(parts) + "."
    if r == "missing field":
        return (f"Chosen COA {d['coa_pdf']} leaves the " + ", ".join(FIELD_LABEL[f] for f in d["missing"]) +
                " blank and the sheet has no value either.")
    if r == "size conflict":
        return (f"Chosen COA {d['coa_pdf']} declares {v['size']} mg; the sheet lists {d['sheet']['Size_mg']} mg and "
                f"price_list.csv has no {d['name']} {v['size']} mg row. Sheet price {d['price']} kept.")
    if r == "purity below 98.0":
        return f"Chosen COA {d['coa_pdf']} (batch {v['batch']}, {v['test_date']}) reports purity {fmt_p(v['purity'])} %."
    if r == "identity failed":
        return (f"Chosen COA {d['coa_pdf']}: observed mass {ch['obs']} Da vs theoretical {ch['theo']} Da "
                f"(difference {abs(ch['obs'] - ch['theo']):.1f} Da > 1.0 Da).")
    if r == "COA older than 12 months":
        return (f"Chosen (newest) COA {d['coa_pdf']} was tested {v['test_date']}, before the cutoff {CUTOFF} "
                f"(reference date {REF}).")
    return ""


def write_exceptions(ctx):
    dec = ctx["dec"]
    out = ["# Exceptions report", "",
           f"Reference date {REF}. Rules: rules.md (v3). Phase: {ctx['phase']}.", "",
           "## 1. Products that are not a clean publish (drafts)", "",
           "| SKU | Product | Issue | Rule | Action taken |", "|---|---|---|---|---|"]
    rule_no = {"no COA": "9, 10", "conflicting COAs": "4, 9", "missing field": "7, 9", "size conflict": "8, 9",
               "purity below 98.0": "9", "identity failed": "9", "COA older than 12 months": "5, 9"}
    for d in dec.values():
        if d["status"] == "draft":
            out.append(f"| {d['sku']} | {d['name']} | {d['reason']}: {reason_detail(d)} | {rule_no[d['reason']]} | "
                       f"Status draft, reason `{d['reason']}`; client asked to {action_for(d)}. |")
    out += ["", "## 2. Values taken from the sheet (blank on the chosen COA)", "",
            "| SKU | Product | Field | Value used | Issue | Rule | Action taken |", "|---|---|---|---|---|---|---|"]
    any_fs = False
    for d in dec.values():
        for f in d["from_sheet"]:
            any_fs = True
            val = d["vals"][f]
            out.append(f"| {d['sku']} | {d['name']} | {f} | {fmt_p(val) if f == 'purity' else val} | "
                       f"{d['coa_pdf']} prints this field blank | 7 | Value taken from products.csv, recorded as \"from sheet\"; "
                       f"older COAs not used for it. |")
    if not any_fs:
        out.append("| - | - | - | - | none | 7 | - |")
    out += ["", "## 3. Sheet and chosen COA disagree", "",
            "COA values override the sheet (rule 6). Size differences follow rule 8.", "",
            "| SKU | Product | Field | Sheet | COA (used) | Rule | Action taken |", "|---|---|---|---|---|---|---|"]
    for d in dec.values():
        if not d["chosen"]:
            if d["reason"] == "conflicting COAs" and d["sheet"]["Batch_Listed"] != d["vals"]["batch"]:
                out.append(f"| {d['sku']} | {d['name']} | batch | {d['sheet']['Batch_Listed']} | {d['vals']['batch']} | 4, 6 | COA batch used |")
            continue
        s, v = d["sheet"], d["vals"]
        pairs = [("batch", s["Batch_Listed"], v["batch"]),
                 ("test_date", s["Test_Date_Listed"], v["test_date"].isoformat() if v["test_date"] else ""),
                 ("purity", s["Purity_Listed_pct"], fmt_p(v["purity"]) if v["purity"] is not None else ""),
                 ("size_mg", s["Size_mg"], str(v["size"]) if v["size"] is not None else "")]
        for f, a, b in pairs:
            if f in [x if x != "size" else "size_mg" for x in d["from_sheet"]] or (f == "test_date" and "test_date" in d["missing"]):
                continue
            if a != b:
                act = "COA value used"
                rule = "6"
                if f == "size_mg":
                    rule = "6, 8"
                    act = ("size and price corrected to the price-list row" if d["size_status"] == "size corrected"
                           else "size conflict: held as draft, sheet price kept")
                out.append(f"| {d['sku']} | {d['name']} | {f} | {a or '(blank)'} | {b} | {rule} | {act} |")
    out += ["", "## 4. Price changes", "", "| SKU | Product | Old | New | Reason | Rule |", "|---|---|---|---|---|---|"]
    for r in ctx["price_changes"]:
        out.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | 8 |")
    if not ctx["price_changes"]:
        out.append("| - | none | | | | 8 |")
    out += ["", "## 5. Products with more than one COA, and every ignored COA result", "",
            "| SKU | Product | COA results | Used | Ignored (why) | Rule |", "|---|---|---|---|---|---|"]
    for d in dec.values():
        if len(d["all_lines"]) > 1 or d["ignored"] or d.get("conflict_lines"):
            allr = ", ".join(f"{x['pdf_file']}{'#'+str(x['line_no']) if x['lab']=='Northgate Peptide Testing' else ''} ({x['batch'] or 'no batch'})" for x in d["all_lines"])
            used = d["coa_pdf"] or "none"
            igs = [f"{x['pdf_file']}{'#'+str(x['line_no']) if x['lab']=='Northgate Peptide Testing' else ''}: {why}" for x, why in d["ignored"]]
            for x in d.get("conflict_lines", []):
                igs.append(f"{x['pdf_file']}: conflicting report for batch {x['batch']}")
            out.append(f"| {d['sku']} | {d['name']} | {allr} | {used} | {'; '.join(igs) or '-'} | 3, 4, 5 |")
    out += ["", "## 6. COA results that matched no product", "",
            "| File | Line | Printed product | Amount | Batch | Issue | Rule | Action taken |", "|---|---|---|---|---|---|---|---|"]
    for ln in ctx["lines"]:
        if not ln["sku"]:
            out.append(f"| {ln['pdf_file']} | {ln['line_no']} | {ln['product_as_printed']} | {ln['mg']} mg | {ln['batch']} | "
                       f"{ln['match_reason']} | 2 | Ignored; not imported |")
    with open(os.path.join(ctx["outdir"], "exceptions_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def action_for(d):
    a = ACTIONS[d["reason"]]
    if d["reason"] == "missing field":
        a = a.format(field=" and ".join(FIELD_LABEL[f] for f in d["missing"]))
    return a


def write_client_email(ctx):
    drafts = [d for d in ctx["dec"].values() if d["status"] == "draft"]
    total = sum(float(d["price"]) for d in drafts)
    pub_n = len(ctx["pub"])
    ctx["draft_total"] = total
    out = ["Subject: COA review - products on hold before go-live", "",
           "Hi,", "",
           f"We've checked every product against its Certificate of Analysis. {pub_n} of 30 products are ready to publish "
           f"({ctx['teaser']}). The products below are saved as drafts until we hear back from you:", ""]
    for d in drafts:
        out.append(f"- **{d['sku']} {d['name']}**: {d['reason']}. Action needed: {action_for(d)}.")
    out += ["", f"**{len(drafts)} draft products, total value USD {total:,.2f}** (sum of their current prices).", "",
            "Price changes we made:"]
    if ctx["price_changes"]:
        for r in ctx["price_changes"]:
            out.append(f"- {r[0]} {r[1]}: {r[2]} → {r[3]} USD ({r[4].split(' (rule')[0]})")
    else:
        out.append("- none")
    out += ["", "Thanks,", "The web team"]
    with open(os.path.join(ctx["outdir"], "client_email.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def write_reading_notes(ctx):
    lines = ctx["lines"]
    out = ["# Reading notes", "",
           "One entry per PDF. Scans (no text layer) were read by eye from the embedded page images, rotated upright and "
           "zoomed where needed; text PDFs were read from the text layer and also checked visually for stamps. "
           "Conversions: NPT dates DD.MM.YYYY, decimal comma, grams; CBA dates MM/DD/YYYY; MAL dates YYYY-MM-DD.", ""]
    byfile = OrderedDict()
    for ln in lines:
        byfile.setdefault(ln["pdf_file"], []).append(ln)
    for f in sorted(byfile, key=lambda x: (x.split("-")[0], x)):
        ll = byfile[f]
        a = ll[0]
        folder = ctx["pdf_dir"](f)
        scan = "scan (no text layer)" if a["scan"] == "yes" else "text PDF"
        out.append(f"## {f}")
        out.append("")
        out.append(f"- Location: `{folder}/{f}`")
        out.append(f"- Lab: {a['lab']}; pages: {a['pages']}; {scan}; orientation: {a['orientation']}; legibility: {a['legibility']}")
        if a["lab"] == "Coastal BioAssay":
            out.append("- Page 1 = Part A purity (material, lot, net content, analysis date, purity); page 2 = Part B identity (theoretical/observed MW). Lot numbers on both pages agree.")
        for ln in ll:
            k = (ln["pdf_file"], ln["line_no"])
            status = ("used" if k in ctx["used"] else "ignored")
            out.append(f"- Result {ln['line_no']}: \"{ln['product_as_printed']}\" | amount {ln['amount_printed'] or '(blank)'} "
                       f"(= {ln['mg']} mg) | lot {ln['batch'] or '(blank)'} | date {ln['date_printed'] or '(blank)'} "
                       f"(= {ln['date'].isoformat() if ln['date'] else 'blank'}) | purity {ln['purity_printed'] or '(blank)'} | "
                       f"mass theor. {ln['theo_printed']} / found {ln['obs_printed']} "
                       f"(diff {abs(ln['obs'] - ln['theo']):.1f} Da)")
            out.append(f"  - Match: {ln['sku'] or 'NONE'}: {ln['match_reason']}")
            if ln["remark"]:
                out.append(f"  - Unusual: {ln['remark']}")
        out.append("")
    if ctx["state"]["void_extra"]:
        out += ["## inbox/MAL-withdrawal-notice.pdf (letter, not a COA)", "",
                "- Location: `inbox/MAL-withdrawal-notice.pdf` (kept in inbox/ as instructed in email 01; not counted as a COA PDF)",
                "- Meridian Analytical Labs; 1 page; scan (no text layer); upright; clear (110 ppi)",
                "- Dated 2026-10-04, \"NOTICE OF REPORT WITHDRAWAL\": report MAL-26-1614 (Semaglutide, lot PP-2607-002) is withdrawn "
                "with immediate effect; the sample was mislabelled at receipt; no replacement report will be issued. Signed Q. Ellison, Laboratory Manager.",
                "- No result lines. Effect: MAL-26-1614.pdf treated as VOID (rule 3).", ""]
    with open(os.path.join(ctx["outdir"], "reading_notes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    ctx = build(sys.argv[1] if len(sys.argv) > 1 else "phase1")
    dec = ctx["dec"]
    print("published", len(ctx["pub"]), "draft", sum(1 for d in dec.values() if d["status"] == "draft"),
          "mean", ctx["mean"], "draft total", ctx["draft_total"])
    for d in dec.values():
        print(d["sku"], d["name"], d["status"], d["reason"], d["vals"]["batch"], d["vals"]["test_date"],
              d["vals"]["purity"], d["vals"]["size"], d["price"], d["coa_pdf"])
