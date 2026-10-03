# Peptide COA build

| Path | What it is |
|---|---|
| `products.csv`, `price_list.csv`, `rules.md`, `coa/`, `inbox/` | Client inputs. `coa/CBA-2655272.pdf` was moved here from `inbox/` per email 02. |
| `output/phase1/` | First delivery (reference date 2026-09-30). |
| `output/final/` | Current state after emails 01–03 (reference date 2026-10-15). Also holds `reply_01–03.md`, `changes_report.md` and `verification_log.md`. |
| `output/steps/after1`, `output/steps/after2` | Intermediate builds after email 01 and 02 (used to attribute each change). |
| `plugin/peptide-coa/` | WordPress plugin: importer, "Certificate of Analysis" product tab, `[coa_library]` shortcode, and `tests/run_tests.php`. |
| `tools/coa_raw.csv`, `tools/coa_raw_email02.csv` | Line-by-line transcription of every COA result as printed. |
| `tools/build.py` | Applies `rules.md` and writes all deliverables: `python3 tools/build.py phase1|after1|after2|final`. |
| `tools/email_changes.py` | The three client follow-ups, applied in date order. |
| `tools/verify.py`, `tools/diff_stages.py` | Independent cross-checks and stage diffs. |

Plugin tests (no WordPress needed):

    cd plugin/peptide-coa
    php tests/run_tests.php ../../output/phase1
    php tests/run_tests.php ../../output/final
