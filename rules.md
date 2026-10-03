# Store rules for COA publishing (v3)

Reference date for all date checks: **2026-09-30**.

## A. Reading the COAs
1. Three labs supply COAs. Each lab uses its own format:
   - Meridian Analytical Labs (MAL-…): dates YYYY-MM-DD, amounts in mg, one result per PDF.
   - Northgate Peptide Testing (NPT-…): dates DD.MM.YYYY, decimal comma, amounts in grams. One PDF can list several lots and several products; each line is a separate result.
   - Coastal BioAssay (CBA-…): dates MM/DD/YYYY, amounts in mg. Two pages: purity on page 1, identity (mass) on page 2.
   Convert every date to YYYY-MM-DD and every amount to whole mg.
2. Labs name products differently (synonyms, spacing, extra words). Match each COA result to a product in products.csv by name, declared amount and theoretical mass together. A result that matches no product is ignored and listed in the exceptions report.
3. A COA stamped VOID is ignored completely.
4. Two reports for the same batch:
   - if one says it is a revision that supersedes the other, use the revision and ignore the superseded report;
   - otherwise, if they disagree on purity, size or mass, the product is held with reason "conflicting COAs". Fill coa_batch and coa_url only; leave the other COA columns blank.
5. Several results with different batches for one product: use the one with the newest test date (after rules 3 and 4).

## B. Final values
6. Values printed on the chosen COA override products.csv for batch, test date, purity and size.
7. Blank field on the chosen COA: if the sheet has a value, use it and record it as "from sheet" in the exceptions report. Do not take values from an older COA. If both are blank, the field is missing.
8. Price: price_list.csv is the source of truth for prices, keyed by product name and size.
   - If the sheet price differs from the price list for the same product and size, the price list wins.
   - If the COA size differs from the sheet size and price_list.csv has a row for the COA size, change the size and the price to that row. This is a "size corrected" case and does not block publishing.
   - If the COA size differs and there is no price row for it, keep the sheet price; the product is held with reason "size conflict".
   Every price that changes goes into price_changes.csv.

## C. Status
9. Status is "publish" only if ALL are true: a COA was used; all four fields (batch, test date, purity, size) are known; there is no size conflict; purity is 98.0 % or higher; observed mass is within 1.0 Da of theoretical mass; the test date is no more than 12 months before the reference date (on or after 2025-09-30).
   Otherwise the status is "draft". Record only the first reason that applies, in this order, using these exact strings:
   `no COA`, `conflicting COAs`, `missing field`, `size conflict`, `purity below 98.0`, `identity failed`, `COA older than 12 months`.
   Published products get status_reason `ok`.
10. If there is no usable COA, leave all coa_* columns blank and use the sheet price.

## D. Outputs
11. COA page URL (published and draft, whenever the batch is known): `https://example-store.test/coa/<sku lowercase>-<batch lowercase>/`. Blank if the batch is unknown.
12. COA library and JSON feed: published products only, newest test date first; ties by SKU. Homepage teaser: `<N> verified COAs · average purity <mean> %`, mean of published purities to 2 decimals.
13. Retest schedule: retest_due = test date + 12 months (same day and month). days_remaining = retest_due minus the reference date. due_soon = yes if days_remaining is 60 or less, otherwise no. Sort by retest_due, then SKU.
14. Featured products: the 3 published products with the highest purity, excluding any with due_soon = yes. Ties: newer test date first, then lower SKU.
15. Supplier scorecard, one row per lab: lab, pdfs_received, results_listed (result lines across that lab's PDFs), results_used (lines chosen as a product's final COA), results_ignored (listed minus used), void_reports, used_but_draft (used lines whose product ended as draft), mean_purity_used (mean purity of used lines that print a purity, 2 decimals).
16. Client email: one entry per draft product in SKU order with the reason and the action needed. Actions:
    no COA → "send a COA"; conflicting COAs → "confirm which report is correct"; missing field → "send a COA showing the missing <field>"; size conflict → "confirm the size and add a price for it"; purity below 98.0 → "retest or replace the batch"; identity failed → "repeat the mass-spec identity test"; COA older than 12 months → "send a COA tested within the last 12 months".
    End with the number of drafts and their total value in USD (sum of their final prices), and a short list of the price changes.
17. Batch numbers use the pattern PP-YYMM-NNN. Keep them exactly as printed.
