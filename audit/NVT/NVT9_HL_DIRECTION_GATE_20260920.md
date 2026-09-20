# NVT9 HL Direction Gate — User-confirmed rule

Audit ID: ID10IQ200  
Date: 2026-09-20  
Status: RULE LOCKED / NOT YET AUTOMATED

## Confirmed visual interpretation

The pink HL line in the user's reference image is the timeframe-local decision line for whether the current swing completes/forms the N-shaped structural transition.

The direction rule is:

- while price has NOT broken that HL, keep the existing trend-following TL direction;
- once price breaks that HL, the eligible TL switches to the breakout side.

This decision is made on the SOURCE timeframe.

Examples:

- H4 evaluates its own H4 HL and selects the H4 TL direction;
- once selected, that exact H4 TL geometry is copied to H4 and D1 under Plan B;
- D1 does not re-run or reinterpret the H4 HL decision.

## Ordering rule

The intended selection order is therefore:

1. Determine source-timeframe HL.
2. Determine whether HL has been broken.
3. From that result, determine the allowed TL direction.
4. Within the allowed direction, choose the relevant TL family.
5. Copy the exact source geometry to Plan-B destination chart(s).

Current-price distance is a relevance filter only AFTER the HL direction gate. It must not override the direction gate.

## Not frozen yet

The user has not yet defined the exact mechanical meaning of "break":

- wick touch / wick penetration;
- candle close beyond HL;
- number of confirming bars;
- tolerance / spread buffer.

Do not automate those details by assumption.

## Current implementation audit

The current preview has the Plan-B source-to-display direction and exact-geometry copy path, but it does NOT yet implement automatic HL-line detection or HL-break gating.

Therefore any current TL direction selected without HL data is a visual/research placeholder, not a completed HL-gated production rule.
