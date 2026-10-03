# Verification log

Covers `output/phase1/` (reference date 2026-09-30) and `output/final/` (after emails 01–03, reference date 2026-10-15). The raw outputs of the automated runs are saved next to this folder:
- `output/verify_output.txt`
- `output/plugin_tests_phase1.txt`
- `output/plugin_tests_final.txt`

## 1. Re-reading every scanned PDF as an image

All 30 scans were re-opened: the 28 in the original `coa/` plus `CBA-2655272.pdf` and `MAL-withdrawal-notice.pdf` from the inbox.
- Each page image was extracted at native resolution (`pdfimages`) and rotated upright where needed.
  - Rotated 90°: MAL-26-1791, MAL-26-2013, CBA-2512337, CBA-2531544.
  - Rotated 180°: MAL-26-7851, CBA-2528977, CBA-2582657.
  - The 72-ppi scans were zoomed 2–2.5×: CBA-2506105, CBA-2509156, CBA-2585319, MAL-26-3028, MAL-26-3363, MAL-26-5744, MAL-26-8104.
- Each value area was then shown next to a caption with the values recorded in `tools/coa_raw.csv`, and compared field by field: product, amount, lot, date, purity, theoretical and observed mass.

| Group | PDFs | Result |
|---|---|---|
| Meridian scans | 1791, 1812, 1950, 2013, 2486, 3028, 3363, 3471, 4657, 5744, 7499, 7851, 7955, 8104, 9779, 9858 | all 16 match |
| Northgate scans | 50433 (4 lines), 99391 (2 lines) | all 6 lines match |
| Coastal scans (both pages) | 2506105, 2509156, 2512337, 2515439, 2528977, 2531544, 2547931, 2574115, 2582657, 2585319, 2655272 | all 11 match; lot numbers agree on page 1 and page 2 |
| Stamps / blanks | VOID on MAL-26-2486 confirmed; blank batch (1791), blank test date (1812) and blank purity (3028) confirmed | lower halves of all Coastal pages checked: footer only, no stamps |
| Withdrawal letter | MAL-withdrawal-notice.pdf | report MAL-26-1614, lot PP-2607-002, dated 2026-10-04 confirmed |

Text-layer PDFs were checked by script: all 18 transcribed lines in the 13 text PDFs appear verbatim in the `pdftotext` output. They were also rendered and inspected by eye for graphic stamps; the only notes found were the Revision 1 and Revision 2 notes on CBA-2566510 and CBA-2528140.

## 2. Automated cross-checks (`python3 tools/verify.py`)

`tools/verify.py` does not reuse `tools/build.py`. It re-derives every product decision independently from `coa_extracted.csv`, `products.csv`, `price_list.csv` and the rules, and then compares the result with each deliverable.

| # | Check | phase1 | final |
|---|---|---|---|
| 1 | Transcription covers every PDF in coa/; scan flag matches the text layer; text PDFs match pdftotext | pass (41 → 42 PDFs) | pass |
| 2 | coa_extracted.csv line count / PDF count | 50 / 41 pass | 51 / 42 pass |
| 3 | reading_notes.md has an entry per PDF and every result line | pass | pass |
| 4 | woocommerce_import.csv: 30 rows; every field equals the independent re-derivation (status, reason, batch, date, purity, size, price, pdf, URL), with batch pattern and date format checked | pass | pass |
| 5 | Provenance: every batch, date, purity and price appears in a COA line, the sheet or the price list | pass | pass |
| 6 | Library = published products, newest test date first, ties by SKU; feed order = library order | 21 pass | 22 pass |
| 7 | Teaser recomputed from the import file (count and mean to 2 dp) matches feed and library | 21 · 98.95 % pass | 22 · 98.93 % pass |
| 8 | Library and feed values equal the import file; every PDF link resolves to a file | pass | pass |
| 9 | Retest schedule recomputed (test date + 12 months, days to reference date, due_soon ≤ 60) | 27 rows pass | 29 rows pass |
| 10 | Featured products recomputed (rule 14) | P14, P27, P01 pass | P14, P27, P01 pass |
| 11 | Supplier scorecard recomputed; results_used total = products with a chosen COA | 28 pass | 30 pass |
| 12 | price_changes.csv = every price differing from the sheet | P11, P16, P25 pass | P11, P16, P25 pass |
| 13 | client_email.md: drafts in SKU order with exact reason and action; total value; price changes | 9 drafts, USD 768.00 pass | 8 drafts, USD 662.00 pass |
| 14 | exceptions_report.md covers every draft, ignored COA result, unmatched result and price change | pass | pass |
| 15 | changes_report.md lists exactly the field differences between the two import files | | 16 / 16 pass |
| 16 | reply_0N.md names every product that email N changed (from the per-email intermediate builds) | | P10 / P18 / P03 pass |

Exact means:
- phase 1: 2078.0 / 21 = 98.952 → 98.95;
- final: 2176.5 / 22 = 98.932 → 98.93.

Neither is a rounding edge case.

Final result: **43 checks passed, 0 failed** (`output/verify_output.txt`).

To check that the verifier is not vacuous, three faults were planted in a copy of the final outputs: P16's price, two feed rows swapped, and the teaser mean. It reported 6 failures: the import values, feed order, teaser, price_changes, changes_report and reply_03. The files were then restored and it returned to 43 / 43. The plugin tests got the same treatment (library row order, feed teaser, and P05 flipped to publish), which gave 11 failures.

Reproducibility: re-running `tools/build.py` for phase1, after1, after2 and final reproduces every output byte-for-byte (`diff -r` against a snapshot shows no differences).

## 3. Mismatches found and what was changed

| # | Found | Cause | Fix | Re-check |
|---|---|---|---|---|
| 1 | After email 02 the counts did not change: P18 was still "no COA" in `output/steps/after2` | "Melanotan II (MT-2)" was missing from the name-synonym table, so the new COA matched no product | Added the synonym to `tools/build.py` and rebuilt after2 and final; all downstream files regenerated | P18 publishes; library, feed, schedule, scorecard and email totals updated; verify passes |
| 2 | reply_01.md contained a garbled duplicate "New values" line | Drafting error | Line removed | Re-read; reply matches the diff |
| 3 | reply_01.md said P10 has 290 days to retest | Hand arithmetic | Checked against retest_schedule.csv (291 days from 2026-09-30) and corrected | Matches the file |
| 4 | Reading notes for the CJC-1295 lines repeated the match reason | Wording bug in the match explanation | Fixed the wording in build.py and rebuilt | phase1 data files otherwise byte-identical |
| 5 | First image re-check: the Meridian crops cut off the observed-mass line, and ImageMagick dropped "%" from the captions | Verification tooling, not data | Re-cropped the Meridian scans taller and escaped "%" | All values compared; no data mismatches found |

No data value recorded from a PDF had to be corrected: the second reading confirmed every transcribed value.

## 4. Interpretations applied (documented so they can be checked)

- **Retest schedule:** lists every product whose final COA test date is known, both published and draft (rule 13 does not restrict it). Products with no usable date are not listed: no COA, conflicting COAs, or a missing test date.
- **Conflicting COAs (P10, phase 1):** only coa_batch and coa_url are filled; coa_pdf is blank too, because it is a COA column. Neither conflicting report counts as "used" in the scorecard.
- **Size conflict (P12):** coa_size_mg shows the size printed on the chosen COA (12 mg, rule 6), and the sheet price is kept (rule 8).
- **Revision rule (rule 4):** CBA-2528140 (Revision 2) supersedes CBA-2566510. MAL-26-1614 and NPT-RS-83434 had no revision relationship, so in phase 1 P10 was held. After email 01, MAL-26-1614 is VOID (rule 3) and P10 uses NPT-RS-83434.
- **Email 03:** "no more than 12 months before the reference date" means a test date on or after 2025-10-15.
- **Withdrawal letter:** it stays in inbox/ and is not counted as a COA PDF in the scorecard. CBA-2655272.pdf was moved to coa/ (git mv) and is counted.

## 5. Plugin test output

`php tests/run_tests.php ../../output/phase1` gives **29 passed, 0 failed** (9 drafts checked for "COA pending").
`php tests/run_tests.php ../../output/final` gives **29 passed, 0 failed** (8 drafts checked). The final run:

```
PASS  import file has 30 data rows
PASS  all 30 rows imported
PASS  no validation errors
PASS  30 WooCommerce products exist after import
PASS  every row stored as product + _coa_* meta exactly as in the CSV
PASS  re-import updates existing products (still 30)
PASS  shortcode renders rows
PASS  shortcode lists the same SKUs in the same order as coa_library.html
PASS  shortcode order matches coa_feed.json
PASS  shortcode lists exactly the published SKUs of the import file
PASS  shortcode batch / test date / purity / URL equal the feed values
PASS  shortcode teaser text matches coa_feed.json
PASS  teaser count matches feed
PASS  teaser mean purity matches feed
PASS  coa_library.html teaser matches feed
PASS  teaser numbers equal the import file (published count and mean purity)
PASS  woocommerce_product_tabs adds a "Certificate of Analysis" tab
PASS  every draft's tab shows "COA pending" and no COA values (8 drafts)
PASS  every published product's tab shows batch, test date, purity, size and the PDF link
PASS  validator rejects bad batch (coa_batch)
PASS  validator rejects bad date (coa_test_date)
PASS  validator rejects bad date format (coa_test_date)
PASS  validator rejects wrong URL (coa_url)
PASS  validator rejects bad status (Status)
PASS  validator rejects bad reason (status_reason)
PASS  validator rejects bad price (Regular price)
PASS  broken row is reported, not imported
PASS  broken row report names batch, date and URL
PASS  rejected row left the stored product meta unchanged

29 passed, 0 failed
```

**Unresolved mismatches: none.**
