# Changes report: phase 1 → final

This report compares `output/phase1/` with `output/final/`. Each change is attributed by rebuilding after each email in date order; the intermediate builds are in `output/steps/after1/` and `output/steps/after2/`, and the diffs come from `tools/diff_stages.py`.

| Email | Date | Content | Effect |
|---|---|---|---|
| email_01 | 2026-10-05 | Meridian withdrawal notice for MAL-26-1614 | report treated as VOID (rule 3) |
| email_02 | 2026-10-08 | Melanotan II COA CBA-2655272.pdf | moved inbox/ → coa/ and processed under the rules |
| email_03 | 2026-10-10 | Launch moved | reference date 2026-10-15 replaces 2026-09-30; 12-month cutoff becomes 2025-10-15 |

## 1. woocommerce_import.csv field differences

16 field changes across 3 products. Every other product and field is identical, including all 30 prices.

| SKU | Product | Field | Phase 1 | Final | Caused by |
|---|---|---|---|---|---|
| P03 | TB-500 | Status | publish | draft | email_03 (test date 2025-10-09 is before the new cutoff 2025-10-15) |
| P03 | TB-500 | status_reason | ok | COA older than 12 months | email_03 |
| P10 | Semaglutide | Status | draft | publish | email_01 (MAL-26-1614 void → only NPT-RS-83434 remains for PP-2607-002) |
| P10 | Semaglutide | coa_test_date | (blank) | 2026-07-18 | email_01 |
| P10 | Semaglutide | coa_purity | (blank) | 98.4 | email_01 |
| P10 | Semaglutide | coa_size_mg | (blank) | 5 | email_01 |
| P10 | Semaglutide | coa_pdf | (blank) | NPT-RS-83434.pdf | email_01 |
| P10 | Semaglutide | status_reason | conflicting COAs | ok | email_01 |
| P18 | Melanotan II | Status | draft | publish | email_02 (new COA CBA-2655272) |
| P18 | Melanotan II | coa_batch | (blank) | PP-2607-015 | email_02 |
| P18 | Melanotan II | coa_test_date | (blank) | 2026-07-09 | email_02 |
| P18 | Melanotan II | coa_purity | (blank) | 99.0 | email_02 |
| P18 | Melanotan II | coa_size_mg | (blank) | 10 | email_02 |
| P18 | Melanotan II | coa_pdf | (blank) | CBA-2655272.pdf | email_02 |
| P18 | Melanotan II | coa_url | (blank) | https://example-store.test/coa/p18-pp-2607-015/ | email_02 |
| P18 | Melanotan II | status_reason | no COA | ok | email_02 |

P10 keeps the same coa_batch (PP-2607-002) and coa_url. In phase 1 they were already filled under the conflicting-COA rule.

## 2. COA library and feed (coa_library.html, coa_feed.json)

| Stage | Published | Teaser | Change |
|---|---|---|---|
| phase 1 | 21 | 21 verified COAs · average purity 98.95 % | |
| after email_01 | 22 | 22 verified COAs · average purity 98.93 % | + P10 (2026-07-18), placed after P02 |
| after email_02 | 23 | 23 verified COAs · average purity 98.93 % | + P18 (2026-07-09), placed after P21 |
| final (after email_03) | 22 | 22 verified COAs · average purity 98.93 % | − P03 (was last, 2025-10-09) |

- Phase 1 order: P27, P11, P01, P16, P20, P29, P19, P13, P25, P02, P21, P06, P09, P22, P26, P17, P04, P14, P15, P30, P03
- Final order: P27, P11, P01, P16, P20, P29, P19, P13, P25, P02, **P10**, P21, **P18**, P06, P09, P22, P26, P17, P04, P14, P15, P30

The library and feed list the same SKUs in the same order in both folders.

## 3. Retest schedule (retest_schedule.csv)

- Rows go from 27 to 29: P10 is added by email_01 (due 2027-07-18) and P18 by email_02 (due 2027-07-09). The schedule lists every product with a known final test date.
- email_03 lowers every days_remaining by 15, because the reference moved from 2026-09-30 to 2026-10-15. Test dates and retest_due dates are unchanged.
- due_soon goes from 4 products (P08, P28, P03, P30) to 5. P15 Selank is added, now 50 days left (it was 65).
- Final days remaining: P08 −56, P28 −33, P03 −6, P30 31, P15 50 (due soon); P14 170 is the next.

## 4. Featured products (featured_products.md)

- Unchanged at every stage: **P14 Epitalon (99.6 %), P27 Oxytocin (99.5 %), P01 BPC-157 (99.4 %)**.
- Excluded as due soon:
  - phase 1: P30 Gonadorelin (99.3 %) and P03 TB-500 (98.9 %);
  - final: P30 Gonadorelin (99.3 %) and P15 Selank (98.7 %). P03 is now a draft, so it isn't a candidate.

## 5. Supplier scorecard (supplier_scorecard.csv)

| Lab | Field | Phase 1 | Final | Caused by |
|---|---|---|---|---|
| Meridian Analytical Labs | void_reports | 1 | 2 | email_01 (MAL-26-1614) |
| Northgate Peptide Testing | results_used | 7 | 8 | email_01 (NPT-RS-83434 Semaglutide line now used for P10) |
| Northgate Peptide Testing | results_ignored | 7 | 6 | email_01 |
| Northgate Peptide Testing | mean_purity_used | 98.74 | 98.70 | email_01 (adds 98.4) |
| Coastal BioAssay | pdfs_received | 15 | 16 | email_02 |
| Coastal BioAssay | results_listed | 15 | 16 | email_02 |
| Coastal BioAssay | results_used | 9 | 10 | email_02 |
| Coastal BioAssay | used_but_draft | 1 | 2 | email_03 (P03 now draft) |

All other cells are unchanged:
- Meridian used 12 and ignored 9 in both folders. MAL-26-1614 was already unused in phase 1 because of the conflict.
- Coastal mean_purity_used stays at 98.97.

## 6. Price changes (price_changes.csv)

No change. The same three price changes apply in both folders:
- P11 Tirzepatide 179.00 → 249.00 (size corrected to 15 mg);
- P16 Semax 48.00 → 52.00;
- P25 GHRP-2 39.00 → 36.00.

## 7. Client email totals (client_email.md)

| Stage | Drafts | Total value USD |
|---|---|---|
| phase 1 | 9 (P05, P07, P08, P10, P12, P18, P23, P24, P28) | 768.00 |
| after email_01 | 8 (−P10 119.00) | 649.00 |
| after email_02 | 7 (−P18 46.00) | 603.00 |
| final | 8 (+P03 59.00): P03, P05, P07, P08, P12, P23, P24, P28 | 662.00 |

## 8. Other files

- `coa_extracted.csv`:
  - adds the CBA-2655272 line (51 lines in total);
  - the MAL-26-1614 note now records the withdrawal/VOID;
  - the NPT-RS-83434 Semaglutide line is now marked USED for P10;
  - the CBA-2551750 note records that P03 is now a draft.
- `reading_notes.md`: adds entries for CBA-2655272.pdf (now in coa/, 42 PDFs) and for the withdrawal letter, which is kept in inbox/ and is not a COA.
- `exceptions_report.md` is updated to match:
  - P10 is no longer a draft. Its sheet/COA differences (purity 99.2 → 98.4, date 2026-07-15 → 2026-07-18) are now listed, and MAL-26-1614 is listed as ignored (withdrawn, VOID).
  - P18 is no longer a draft.
  - P03 is now a draft (COA older than 12 months).
