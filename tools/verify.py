#!/usr/bin/env python3
"""Independent cross-checks of the deliverables (does not import build.py).

For each folder (phase1, final) it re-derives the decisions from coa_extracted.csv,
products.csv, price_list.csv and the rules, and checks every deliverable agrees.
Prints one line per check; exit code 1 if anything fails."""
import csv, json, re, os, subprocess, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []
LOG = []


def check(ok, label, detail=""):
    LOG.append(("PASS" if ok else "FAIL") + "  " + label + ("" if ok or not detail else f"\n      {detail}"))
    if not ok:
        FAILS.append(label)


def rd(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


products = {r["SKU"]: r for r in rd(os.path.join(ROOT, "products.csv"))}
prices = {(r["Product"], int(r["Size_mg"])): r["Price_USD"] for r in rd(os.path.join(ROOT, "price_list.csv"))}

# ------------------------------------------------------------ 0. text-layer PDFs vs transcription
raw = rd(os.path.join(ROOT, "tools", "coa_raw.csv")) + rd(os.path.join(ROOT, "tools", "coa_raw_email02.csv"))
bad = []
n_text = 0
for r in raw:
    if r["scan"] == "no":
        n_text += 1
        txt = subprocess.run(["pdftotext", "-layout", os.path.join(ROOT, "coa", r["pdf_file"]), "-"],
                             capture_output=True, text=True).stdout
        for k in ["product_as_printed", "amount_printed", "batch", "date_printed", "purity_printed", "theo_printed", "obs_printed"]:
            if r[k] and r[k] not in txt:
                bad.append(f"{r['pdf_file']} {k}={r[k]}")
check(not bad, f"text-layer PDFs: all {n_text} transcribed result lines found verbatim in pdftotext output", "; ".join(bad))
pdfs_on_disk = sorted(f for f in os.listdir(os.path.join(ROOT, "coa")) if f.endswith(".pdf"))
check(sorted({r["pdf_file"] for r in raw}) == pdfs_on_disk, f"transcription covers every PDF in coa/ ({len(pdfs_on_disk)})")
for r in raw:
    if r["scan"] == "no":
        continue
txtless = []
for f in pdfs_on_disk:
    t = subprocess.run(["pdftotext", os.path.join(ROOT, "coa", f), "-"], capture_output=True, text=True).stdout.strip()
    scan_flag = next(r["scan"] for r in raw if r["pdf_file"] == f)
    if (t == "") != (scan_flag == "yes"):
        txtless.append(f)
check(not txtless, "scan/text flag in transcription matches the presence of a text layer", ", ".join(txtless))


def add12(d):
    return date(d.year + 1, d.month, d.day)


def verify(folder, ref, n_pdfs_expected, n_lines_expected):
    out = os.path.join(ROOT, "output", folder)
    cutoff = date(ref.year - 1, ref.month, ref.day)
    tag = f"[{folder}]"
    ext = rd(os.path.join(out, "coa_extracted.csv"))
    check(len(ext) == n_lines_expected, f"{tag} coa_extracted.csv has {n_lines_expected} result lines", str(len(ext)))
    check(len({e['pdf_file'] for e in ext}) == n_pdfs_expected, f"{tag} coa_extracted.csv covers {n_pdfs_expected} PDFs")
    notes = open(os.path.join(out, "reading_notes.md"), encoding="utf-8").read()
    per_pdf = {}
    for e in ext:
        per_pdf[e["pdf_file"]] = per_pdf.get(e["pdf_file"], 0) + 1
    miss = []
    for f, n in per_pdf.items():
        sec = notes.split(f"## {f}\n", 1)
        if len(sec) < 2:
            miss.append(f + " (no entry)")
            continue
        body = sec[1].split("\n## ", 1)[0]
        if body.count("- Result ") != n:
            miss.append(f"{f} ({body.count('- Result ')} vs {n})")
        for e in ext:
            if e["pdf_file"] == f and e["batch"] and e["batch"] not in body:
                miss.append(f"{f} batch {e['batch']}")
    check(not miss, f"{tag} reading_notes.md has an entry per PDF and every result line of coa_extracted.csv", "; ".join(miss))

    # ---------------------------------------------------- independent decisions
    def f_or_none(x):
        return float(x) if x != "" else None
    lines = []
    for e in ext:
        lines.append(dict(e, purity_f=f_or_none(e["purity"]), theo=f_or_none(e["theoretical_mass"]), obs=f_or_none(e["observed_mass"]),
                          mg=int(e["declared_amount_mg"]), d=date.fromisoformat(e["test_date"]) if e["test_date"] else None,
                          void="VOID" in e["notes"] and "IGNORED" in e["notes"], superseded="superseded by revision" in e["notes"]))
    exp = {}
    for sku, p in products.items():
        mine = [l for l in lines if l["matched_sku"] == sku and not l["void"] and not l["superseded"]]
        size = int(p["Size_mg"])
        listp = prices.get((p["Product"], size))
        price = listp if listp else p["Price_USD"]
        row = dict(SKU=sku, Name=p["Product"], price=price, batch="", date="", purity="", size="", pdf="", url="", reason=None)
        if not mine:
            row["reason"] = "no COA"
            row["price"] = p["Price_USD"] if not listp else listp
        else:
            newest = max(mine, key=lambda l: l["d"] or date.min)
            same = [l for l in mine if l["batch"] == newest["batch"]]
            if len(same) > 1 and len({(l["purity_f"], l["mg"], l["theo"], l["obs"]) for l in same}) > 1:
                row.update(reason="conflicting COAs", batch=newest["batch"])
            else:
                c = newest
                b = c["batch"] or p["Batch_Listed"]
                dt = c["test_date"] or p["Test_Date_Listed"]
                pu = c["purity"] or (f"{float(p['Purity_Listed_pct']):.1f}" if p["Purity_Listed_pct"] else "")
                sz = c["mg"]
                row.update(batch=b, date=dt, purity=pu, size=str(sz), pdf=c["pdf_file"])
                if sz != size:
                    if (p["Product"], sz) in prices:
                        row["price"] = prices[(p["Product"], sz)]
                        sc = False
                    else:
                        row["price"] = p["Price_USD"]
                        sc = True
                else:
                    sc = False
                if not b or not dt or not pu:
                    row["reason"] = "missing field"
                elif sc:
                    row["reason"] = "size conflict"
                elif float(pu) < 98.0:
                    row["reason"] = "purity below 98.0"
                elif abs(c["obs"] - c["theo"]) > 1.0:
                    row["reason"] = "identity failed"
                elif date.fromisoformat(dt) < cutoff:
                    row["reason"] = "COA older than 12 months"
                else:
                    row["reason"] = "ok"
        if row["batch"]:
            row["url"] = f"https://example-store.test/coa/{sku.lower()}-{row['batch'].lower()}/"
        exp[sku] = row
    imp = rd(os.path.join(out, "woocommerce_import.csv"))
    check(len(imp) == 30, f"{tag} woocommerce_import.csv has 30 rows")
    mism = []
    for r in imp:
        e = exp[r["SKU"]]
        want = {"Name": e["Name"], "Regular price": e["price"], "Status": "publish" if e["reason"] == "ok" else "draft",
                "coa_batch": e["batch"], "coa_test_date": e["date"], "coa_purity": e["purity"], "coa_size_mg": e["size"],
                "coa_pdf": e["pdf"], "coa_url": e["url"], "status_reason": e["reason"]}
        for k, v in want.items():
            if r[k] != v:
                mism.append(f"{r['SKU']} {k}: file '{r[k]}' vs re-derived '{v}'")
        if r["coa_batch"] and not re.fullmatch(r"PP-\d{4}-\d{3}", r["coa_batch"]):
            mism.append(f"{r['SKU']} batch pattern")
        if r["coa_test_date"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["coa_test_date"]):
            mism.append(f"{r['SKU']} date format")
    check(not mism, f"{tag} every import value equals an independent re-derivation from the COA lines, sheet, price list and rules", "; ".join(mism))

    # provenance: every value exists in a source
    prov = []
    for r in imp:
        p = products[r["SKU"]]
        srcl = [l for l in lines if l["matched_sku"] == r["SKU"]]
        if r["coa_batch"] and r["coa_batch"] not in [l["batch"] for l in srcl] + [p["Batch_Listed"]]:
            prov.append(f"{r['SKU']} batch")
        if r["coa_test_date"] and r["coa_test_date"] not in [l["test_date"] for l in srcl] + [p["Test_Date_Listed"]]:
            prov.append(f"{r['SKU']} date")
        if r["coa_purity"] and float(r["coa_purity"]) not in [l["purity_f"] for l in srcl] + [float(p["Purity_Listed_pct"])]:
            prov.append(f"{r['SKU']} purity")
        if r["Regular price"] not in list(prices.values()) + [p["Price_USD"]]:
            prov.append(f"{r['SKU']} price")
    check(not prov, f"{tag} every batch/date/purity/price in the import file exists in a COA line, the sheet or the price list", ", ".join(prov))

    # ---------------------------------------------------- library / feed / teaser
    pub = [r for r in imp if r["Status"] == "publish"]
    order = [r["SKU"] for r in sorted(sorted(pub, key=lambda r: r["SKU"]), key=lambda r: r["coa_test_date"], reverse=True)]
    html = open(os.path.join(out, "coa_library.html"), encoding="utf-8").read()
    lib = re.findall(r'<tr data-sku="([^"]+)"', html)
    feed = json.load(open(os.path.join(out, "coa_feed.json"), encoding="utf-8"))
    fsk = [p["sku"] for p in feed["products"]]
    check(lib == order, f"{tag} library = published products, newest test date first, ties by SKU ({len(lib)})", f"{lib} vs {order}")
    check(fsk == order, f"{tag} feed order = library order")
    n = len(pub)
    mean = round(sum(float(r["coa_purity"]) for r in pub) / n + 1e-12, 2)
    teaser = f"{n} verified COAs · average purity {mean:.2f} %"
    check(feed["teaser"]["text"] == teaser and feed["teaser"]["verified_coas"] == n and abs(feed["teaser"]["average_purity"] - mean) < 1e-9,
          f"{tag} feed teaser '{teaser}' recomputed from the import file")
    check(f'id="coa-teaser">{teaser}<' in html, f"{tag} library teaser matches")
    fv = []
    byk = {r["SKU"]: r for r in imp}
    for p in feed["products"]:
        r = byk[p["sku"]]
        if (p["batch"], p["test_date"], f"{p['purity']:.1f}", p["coa_url"], p["product"]) != (r["coa_batch"], r["coa_test_date"], r["coa_purity"], r["coa_url"], r["Name"]):
            fv.append(p["sku"])
        if not os.path.isfile(os.path.join(ROOT, p["coa_pdf"])):
            fv.append(p["sku"] + " pdf missing")
    hv = []
    for m in re.finditer(r'<tr data-sku="([^"]+)"><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*) %</td><td><a href="([^"]+)">', html):
        r = byk[m.group(1)]
        if (m.group(3), m.group(4), m.group(5)) != (r["coa_batch"], r["coa_test_date"], r["coa_purity"]):
            hv.append(m.group(1))
        if not os.path.isfile(os.path.normpath(os.path.join(out, m.group(6)))):
            hv.append(m.group(1) + " link broken")
    check(not fv and not hv, f"{tag} library and feed values equal the import file and every PDF link resolves", ", ".join(fv + hv))

    # ---------------------------------------------------- retest schedule
    rs = rd(os.path.join(out, "retest_schedule.csv"))
    want = []
    for r in imp:
        if r["coa_test_date"]:
            td = date.fromisoformat(r["coa_test_date"])
            due = add12(td)
            days = (due - ref).days
            want.append([r["SKU"], r["Name"], r["coa_test_date"], due.isoformat(), str(days), "yes" if days <= 60 else "no"])
    want.sort(key=lambda x: (x[3], x[0]))
    got = [[x["SKU"], x["Name"], x["test_date"], x["retest_due"], x["days_remaining"], x["due_soon"]] for x in rs]
    check(got == want, f"{tag} retest schedule recomputed from import test dates (ref {ref}, {len(want)} rows)")
    due_soon = {x[0]: x[5] for x in want}

    # ---------------------------------------------------- featured
    cand = [r for r in pub if due_soon[r["SKU"]] == "no"]
    cand.sort(key=lambda r: r["SKU"])
    cand.sort(key=lambda r: r["coa_test_date"], reverse=True)
    cand.sort(key=lambda r: float(r["coa_purity"]), reverse=True)
    feat = [r["SKU"] for r in cand[:3]]
    ft = open(os.path.join(out, "featured_products.md"), encoding="utf-8").read()
    got = re.findall(r"^\| \d \| (P\d\d) \| [^|]+ \| ([\d.]+) % \| ([\d-]+) \|", ft, re.M)
    check([g[0] for g in got] == feat and all(byk[s]["coa_purity"] == p and byk[s]["coa_test_date"] == d for s, p, d in got),
          f"{tag} featured products = {feat}")

    # ---------------------------------------------------- scorecard
    sc = {r["lab"]: r for r in rd(os.path.join(out, "supplier_scorecard.csv"))}
    used_keys = {(r["coa_pdf"], r["SKU"]) for r in imp if r["coa_pdf"] and r["status_reason"] not in ("conflicting COAs", "no COA")}
    scb = []
    for lab in ["Meridian Analytical Labs", "Northgate Peptide Testing", "Coastal BioAssay"]:
        ll = [l for l in lines if l["lab"] == lab]
        u = [l for l in ll if (l["pdf_file"], l["matched_sku"]) in used_keys and "USED" in l["notes"]]
        pur = [l["purity_f"] for l in u if l["purity_f"] is not None]
        w = {"pdfs_received": str(len({l["pdf_file"] for l in ll})), "results_listed": str(len(ll)), "results_used": str(len(u)),
             "results_ignored": str(len(ll) - len(u)), "void_reports": str(len({l["pdf_file"] for l in ll if l["void"]})),
             "used_but_draft": str(sum(1 for l in u if byk[l["matched_sku"]]["Status"] == "draft")),
             "mean_purity_used": f"{round(sum(pur) / len(pur) + 1e-12, 2):.2f}"}
        for k, v in w.items():
            if sc[lab][k] != v:
                scb.append(f"{lab} {k} {sc[lab][k]} vs {v}")
    tot_used = sum(int(sc[l]["results_used"]) for l in sc)
    check(not scb, f"{tag} supplier scorecard recomputed from coa_extracted.csv + import file", "; ".join(scb))
    check(tot_used == sum(1 for r in imp if r["coa_pdf"]), f"{tag} scorecard results_used total ({tot_used}) = products with a chosen COA")

    # ---------------------------------------------------- price changes
    pc = rd(os.path.join(out, "price_changes.csv"))
    want = [(r["SKU"], products[r["SKU"]]["Price_USD"], r["Regular price"]) for r in imp if r["Regular price"] != products[r["SKU"]]["Price_USD"]]
    check([(r["SKU"], r["old_price"], r["new_price"]) for r in pc] == want, f"{tag} price_changes.csv = every price differing from the sheet {[w[0] for w in want]}")

    # ---------------------------------------------------- client email
    em = open(os.path.join(out, "client_email.md"), encoding="utf-8").read()
    drafts = [r for r in imp if r["Status"] == "draft"]
    entries = re.findall(r"^- \*\*(P\d\d) [^*]+\*\*: ([^.]+(?:\.0)?)\. Action needed: (.+)\.$", em, re.M)
    acts = {"no COA": "send a COA", "conflicting COAs": "confirm which report is correct",
            "size conflict": "confirm the size and add a price for it", "purity below 98.0": "retest or replace the batch",
            "identity failed": "repeat the mass-spec identity test",
            "COA older than 12 months": "send a COA tested within the last 12 months"}
    ok = [e[0] for e in entries] == [r["SKU"] for r in drafts]
    for (s, reason, act), r in zip(entries, drafts):
        exp_act = acts.get(r["status_reason"]) or ("send a COA showing the missing " + ("test date" if not r["coa_test_date"] else "batch number" if not r["coa_batch"] else "purity"))
        ok = ok and reason == r["status_reason"] and act == exp_act
    total = sum(float(r["Regular price"]) for r in drafts)
    ok_tot = f"**{len(drafts)} draft products, total value USD {total:,.2f}**" in em
    ok_pc = all(f"- {r['SKU']} " in em for r in pc)
    check(ok and ok_tot and ok_pc, f"{tag} client email: {len(drafts)} drafts in SKU order with reason + action, total USD {total:.2f}, price changes listed")

    # ---------------------------------------------------- exceptions report
    ex = open(os.path.join(out, "exceptions_report.md"), encoding="utf-8").read()
    missing = [r["SKU"] for r in drafts if f"| {r['SKU']} | {r['Name']} | {r['status_reason']}:" not in ex]
    for l in lines:
        if not l["matched_sku"] and l["pdf_file"] not in ex.split("## 6.")[1]:
            missing.append(l["pdf_file"])
        if "IGNORED" in l["notes"] and l["matched_sku"] and l["pdf_file"] not in ex.split("## 5.")[1]:
            missing.append("ignored " + l["pdf_file"])
    for r in pc:
        if f"| {r['SKU']} | {r['Name']} | {r['old_price']} | {r['new_price']} |" not in ex:
            missing.append("price " + r["SKU"])
    check(not missing, f"{tag} exceptions report covers every draft, ignored/unmatched COA result and price change", ", ".join(missing))
    return {"pub": n, "draft": len(drafts), "mean": mean, "total": total, "featured": feat}


s1 = verify("phase1", date(2026, 9, 30), 41, 50)
s2 = verify("final", date(2026, 10, 15), 42, 51)

# ------------------------------------------------------------ changes report vs real diff
a = {r["SKU"]: r for r in rd(os.path.join(ROOT, "output", "phase1", "woocommerce_import.csv"))}
b = {r["SKU"]: r for r in rd(os.path.join(ROOT, "output", "final", "woocommerce_import.csv"))}
diffs = [(s, k, a[s][k], b[s][k]) for s in a for k in a[s] if a[s][k] != b[s][k]]
cr = open(os.path.join(ROOT, "output", "final", "changes_report.md"), encoding="utf-8").read()
rows = re.findall(r"^\| (P\d\d) \| [^|]+ \| ([^|]+) \| ([^|]+) \| ([^|]+) \| email_0\d", cr, re.M)
norm = lambda x: "" if x.strip() == "(blank)" else x.strip()
listed = [(s, k.strip(), norm(o), norm(n)) for s, k, o, n in rows]
check(sorted(listed) == sorted(diffs), f"changes_report.md lists exactly the {len(diffs)} field differences between the two import files",
      f"listed {len(listed)}; missing {set(diffs) - set(listed)}; extra {set(listed) - set(diffs)}")
for i, (old, new) in enumerate([("phase1", "steps/after1"), ("steps/after1", "steps/after2"), ("steps/after2", "final")], 1):
    pa = {r["SKU"]: r for r in rd(os.path.join(ROOT, "output", old, "woocommerce_import.csv"))}
    pb = {r["SKU"]: r for r in rd(os.path.join(ROOT, "output", new, "woocommerce_import.csv"))}
    skus = sorted({s for s in pa for k in pa[s] if pa[s][k] != pb[s][k]})
    reply = open(os.path.join(ROOT, "output", "final", f"reply_0{i}.md"), encoding="utf-8").read()
    check(all(s in reply for s in skus) and skus, f"reply_0{i}.md names every product changed by email_0{i}: {skus}")

print("\n".join(LOG))
print(f"\nphase1: {s1}\nfinal:  {s2}")
print(f"\n{len(LOG) - len(FAILS)} checks passed, {len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
