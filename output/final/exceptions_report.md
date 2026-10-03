# Exceptions report

Reference date 2026-10-15. Rules: rules.md (v3). Phase: final.

## 1. Products that are not a clean publish (drafts)

| SKU | Product | Issue | Rule | Action taken |
|---|---|---|---|---|
| P03 | TB-500 | COA older than 12 months: Chosen (newest) COA CBA-2551750.pdf was tested 2025-10-09, before the cutoff 2025-10-15 (reference date 2026-10-15). | 5, 9 | Status draft, reason `COA older than 12 months`; client asked to send a COA tested within the last 12 months. |
| P05 | Ipamorelin | purity below 98.0: Chosen COA MAL-26-2186.pdf (batch PP-2608-016, 2026-08-20) reports purity 97.6 %. | 9 | Status draft, reason `purity below 98.0`; client asked to retest or replace the batch. |
| P07 | CJC-1295 (with DAC) | identity failed: Chosen COA NPT-RS-84830.pdf: observed mass 3651.0 Da vs theoretical 3647.2 Da (difference 3.8 Da > 1.0 Da). | 9 | Status draft, reason `identity failed`; client asked to repeat the mass-spec identity test. |
| P08 | Sermorelin | COA older than 12 months: Chosen (newest) COA MAL-26-1950.pdf was tested 2025-08-20, before the cutoff 2025-10-15 (reference date 2026-10-15). | 5, 9 | Status draft, reason `COA older than 12 months`; client asked to send a COA tested within the last 12 months. |
| P12 | Retatrutide | size conflict: Chosen COA NPT-RS-83434.pdf declares 12 mg; the sheet lists 10 mg and price_list.csv has no Retatrutide 12 mg row. Sheet price 229.00 kept. | 8, 9 | Status draft, reason `size conflict`; client asked to confirm the size and add a price for it. |
| P23 | LL-37 | purity below 98.0: Chosen COA NPT-RS-83434.pdf (batch PP-2608-007, 2026-08-22) reports purity 96.9 %. | 9 | Status draft, reason `purity below 98.0`; client asked to retest or replace the batch. |
| P24 | Hexarelin | missing field: Chosen COA MAL-26-1812.pdf leaves the test date blank and the sheet has no value either. | 7, 9 | Status draft, reason `missing field`; client asked to send a COA showing the missing test date. |
| P28 | KPV | COA older than 12 months: Chosen (newest) COA CBA-2554937.pdf was tested 2025-09-12, before the cutoff 2025-10-15 (reference date 2026-10-15). | 5, 9 | Status draft, reason `COA older than 12 months`; client asked to send a COA tested within the last 12 months. |

## 2. Values taken from the sheet (blank on the chosen COA)

| SKU | Product | Field | Value used | Issue | Rule | Action taken |
|---|---|---|---|---|---|---|
| P04 | GHK-Cu | batch | PP-2605-008 | MAL-26-1791.pdf prints this field blank | 7 | Value taken from products.csv, recorded as "from sheet"; older COAs not used for it. |
| P19 | DSIP | purity | 98.8 | MAL-26-3028.pdf prints this field blank | 7 | Value taken from products.csv, recorded as "from sheet"; older COAs not used for it. |

## 3. Sheet and chosen COA disagree

COA values override the sheet (rule 6). Size differences follow rule 8.

| SKU | Product | Field | Sheet | COA (used) | Rule | Action taken |
|---|---|---|---|---|---|---|
| P01 | BPC-157 | batch | PP-2607-004 | PP-2608-003 | 6 | COA value used |
| P01 | BPC-157 | test_date | 2026-07-20 | 2026-08-12 | 6 | COA value used |
| P05 | Ipamorelin | batch | PP-2601-010 | PP-2608-016 | 6 | COA value used |
| P05 | Ipamorelin | test_date | 2026-01-14 | 2026-08-20 | 6 | COA value used |
| P05 | Ipamorelin | purity | 98.4 | 97.6 | 6 | COA value used |
| P08 | Sermorelin | batch | PP-2602-006 | PP-2507-020 | 6 | COA value used |
| P08 | Sermorelin | test_date | 2026-02-10 | 2025-08-20 | 6 | COA value used |
| P10 | Semaglutide | test_date | 2026-07-15 | 2026-07-18 | 6 | COA value used |
| P10 | Semaglutide | purity | 99.2 | 98.4 | 6 | COA value used |
| P11 | Tirzepatide | size_mg | 10 | 15 | 6, 8 | size and price corrected to the price-list row |
| P12 | Retatrutide | size_mg | 10 | 12 | 6, 8 | size conflict: held as draft, sheet price kept |
| P15 | Selank | batch | PP-2608-005 | PP-2512-018 | 6 | COA value used |
| P15 | Selank | test_date | 2026-08-14 | 2025-12-04 | 6 | COA value used |
| P15 | Selank | purity | 99.1 | 98.7 | 6 | COA value used |
| P20 | Kisspeptin-10 | batch | PP-2602-003 | PP-2608-010 | 6 | COA value used |
| P20 | Kisspeptin-10 | test_date | 2026-02-08 | 2026-08-02 | 6 | COA value used |
| P20 | Kisspeptin-10 | purity | 99.1 | 98.6 | 6 | COA value used |
| P26 | GHRP-6 | batch | PP-2601-019 | PP-2606-025 | 6 | COA value used |
| P26 | GHRP-6 | test_date | 2026-01-21 | 2026-06-16 | 6 | COA value used |

## 4. Price changes

| SKU | Product | Old | New | Reason | Rule |
|---|---|---|---|---|---|
| P11 | Tirzepatide | 179.00 | 249.00 | size corrected: COA declares 15 mg, sheet 10 mg; price list row Tirzepatide 15 mg (rule 8) | 8 |
| P16 | Semax | 48.00 | 52.00 | price list differs from sheet price (rule 8) | 8 |
| P25 | GHRP-2 | 39.00 | 36.00 | price list differs from sheet price (rule 8) | 8 |

## 5. Products with more than one COA, and every ignored COA result

| SKU | Product | COA results | Used | Ignored (why) | Rule |
|---|---|---|---|---|---|
| P01 | BPC-157 | MAL-26-3471.pdf (PP-2510-012), MAL-26-6305.pdf (PP-2608-003) | MAL-26-6305.pdf | MAL-26-3471.pdf: older batch than chosen PP-2608-003 (rule 5) | 3, 4, 5 |
| P02 | BPC-157 | NPT-RS-33688.pdf#1 (PP-2602-008), NPT-RS-84830.pdf#1 (PP-2607-021) | NPT-RS-84830.pdf | NPT-RS-33688.pdf#1: older batch than chosen PP-2607-021 (rule 5) | 3, 4, 5 |
| P03 | TB-500 | CBA-2551750.pdf (PP-2509-007), CBA-2585319.pdf (PP-2502-004) | CBA-2551750.pdf | CBA-2585319.pdf: older batch than chosen PP-2509-007 (rule 5) | 3, 4, 5 |
| P05 | Ipamorelin | MAL-26-2186.pdf (PP-2608-016), MAL-26-9779.pdf (PP-2601-010) | MAL-26-2186.pdf | MAL-26-9779.pdf: older batch than chosen PP-2608-016 (rule 5) | 3, 4, 5 |
| P06 | CJC-1295 (no DAC) | CBA-2512337.pdf (PP-2606-017), CBA-2547931.pdf (PP-2512-005) | CBA-2512337.pdf | CBA-2547931.pdf: older batch than chosen PP-2606-017 (rule 5) | 3, 4, 5 |
| P09 | Tesamorelin | CBA-2528140.pdf (PP-2606-014), CBA-2566510.pdf (PP-2606-014) | CBA-2528140.pdf | CBA-2566510.pdf: superseded by revision CBA-2528140.pdf (rule 4) | 3, 4, 5 |
| P10 | Semaglutide | MAL-26-1614.pdf (PP-2607-002), NPT-RS-83434.pdf#1 (PP-2607-002) | NPT-RS-83434.pdf | MAL-26-1614.pdf: withdrawn by the lab, treated as VOID per email 01 (rule 3) | 3, 4, 5 |
| P13 | AOD-9604 | MAL-26-7851.pdf (PP-2603-014), MAL-26-8104.pdf (PP-2607-009) | MAL-26-8104.pdf | MAL-26-7851.pdf: older batch than chosen PP-2607-009 (rule 5) | 3, 4, 5 |
| P14 | Epitalon | CBA-2509156.pdf (PP-2603-022), CBA-2531544.pdf (PP-2510-009) | CBA-2509156.pdf | CBA-2531544.pdf: older batch than chosen PP-2603-022 (rule 5) | 3, 4, 5 |
| P15 | Selank | MAL-26-2486.pdf (PP-2608-005), MAL-26-7955.pdf (PP-2512-018) | MAL-26-7955.pdf | MAL-26-2486.pdf: stamped VOID (rule 3) | 3, 4, 5 |
| P16 | Semax | NPT-RS-84830.pdf#2 (PP-2608-002), NPT-RS-99391.pdf#2 (PP-2510-011) | NPT-RS-84830.pdf | NPT-RS-99391.pdf#2: older batch than chosen PP-2608-002 (rule 5) | 3, 4, 5 |
| P17 | PT-141 | CBA-2507747.pdf (PP-2606-030), CBA-2574115.pdf (PP-2601-027) | CBA-2507747.pdf | CBA-2574115.pdf: older batch than chosen PP-2606-030 (rule 5) | 3, 4, 5 |
| P19 | DSIP | MAL-26-3028.pdf (PP-2607-024), MAL-26-4657.pdf (PP-2603-002) | MAL-26-3028.pdf | MAL-26-4657.pdf: older batch than chosen PP-2607-024 (rule 5) | 3, 4, 5 |
| P20 | Kisspeptin-10 | NPT-RS-50433.pdf#1 (PP-2602-003), NPT-RS-50433.pdf#2 (PP-2608-010), NPT-RS-50433.pdf#3 (PP-2605-001) | NPT-RS-50433.pdf | NPT-RS-50433.pdf#3: older batch than chosen PP-2608-010 (rule 5); NPT-RS-50433.pdf#1: older batch than chosen PP-2608-010 (rule 5) | 3, 4, 5 |
| P22 | Thymosin Alpha-1 | MAL-26-2013.pdf (PP-2606-012), MAL-26-7499.pdf (PP-2512-022) | MAL-26-2013.pdf | MAL-26-7499.pdf: older batch than chosen PP-2606-012 (rule 5) | 3, 4, 5 |
| P25 | GHRP-2 | CBA-2506105.pdf (PP-2511-003), CBA-2528977.pdf (PP-2607-012) | CBA-2528977.pdf | CBA-2506105.pdf: older batch than chosen PP-2607-012 (rule 5) | 3, 4, 5 |
| P26 | GHRP-6 | MAL-26-3181.pdf (PP-2606-025), MAL-26-5744.pdf (PP-2601-019) | MAL-26-3181.pdf | MAL-26-5744.pdf: older batch than chosen PP-2606-025 (rule 5) | 3, 4, 5 |
| P29 | Cagrilintide | MAL-26-3363.pdf (PP-2607-030), MAL-26-9858.pdf (PP-2603-017) | MAL-26-3363.pdf | MAL-26-9858.pdf: older batch than chosen PP-2607-030 (rule 5) | 3, 4, 5 |

## 6. COA results that matched no product

| File | Line | Printed product | Amount | Batch | Issue | Rule | Action taken |
|---|---|---|---|---|---|---|---|
| NPT-RS-33688.pdf | 2 | Thymosin Beta-4 (full length) | 5 mg | PP-2606-040 | no product in products.csv is 'Thymosin Beta-4 (full length)' (theoretical mass 4963.4 Da) | 2 | Ignored; not imported |
| NPT-RS-50433.pdf | 4 | Pinealon | 10 mg | PP-2607-033 | no product in products.csv is 'Pinealon' (theoretical mass 359.4 Da) | 2 | Ignored; not imported |
