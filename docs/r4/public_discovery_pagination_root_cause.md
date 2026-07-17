# Public discovery pagination root cause

Confirmed cause: `BACKEND_STOPS_AFTER_FIRST_EIS_PAGE` and `PAGE_SIZE_CLAMPED` semantics. The UI requested 50 cards, but the backend passed 50 as the expected physical EIS page size. EIS returned its normal 10-card page; the `len(page_cards) < effective_page_size` condition incorrectly marked the source exhausted, so no cursor was returned.

The correction separates physical EIS page size (10) from the requested unique-card limit, and continues through physical pages until the requested limit, source exhaustion, or a safe backfill cap.
