"""Client follow-ups from inbox/, applied in date order (Part 3)."""
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply(state, n):
    if n == 1:
        # email_01.md (2026-10-05): Meridian withdrawal notice (inbox/MAL-withdrawal-notice.pdf, dated 2026-10-04)
        # withdraws MAL-26-1614 (Semaglutide, lot PP-2607-002). Treat that report as VOID.
        state["void_extra"]["MAL-26-1614.pdf"] = (
            "VOID: withdrawn by Meridian notice of 2026-10-04 (inbox/MAL-withdrawal-notice.pdf, email 01) - "
            "sample mislabelled at receipt, no replacement report")
        state["events"].append("email 01: MAL-26-1614.pdf treated as VOID")
    elif n == 2:
        # email_02.md (2026-10-08): Melanotan II COA CBA-2655272.pdf, moved into coa/.
        state["extra_raw"] = os.path.join(ROOT, "tools", "coa_raw_email02.csv")
        state["events"].append("email 02: CBA-2655272.pdf (Melanotan II) added to coa/")
    elif n == 3:
        # email_03.md (2026-10-10): reference date 2026-10-15 replaces 2026-09-30 for every rule.
        state["ref"] = date(2026, 10, 15)
        state["cutoff"] = date(2025, 10, 15)
        state["events"].append("email 03: reference date 2026-10-15 (12-month cutoff 2025-10-15)")
