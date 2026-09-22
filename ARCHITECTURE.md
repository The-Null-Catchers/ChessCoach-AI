# Architecture

## Service boundaries

- **API service:** authentication, authorization, imports, queries, training interactions.
- **Analysis worker:** Stockfish execution and deterministic chess calculations.
- **Coaching worker (next phase):** structured LLM explanations from engine facts and detected themes.
- **Aggregation worker (next phase):** weakness confidence, trends, opening/endgame stats and weekly reports.
- **Web/Mobile:** presentation, interaction and offline synchronization; never objective evaluation authority.

## Analysis invariants

1. Stockfish is authoritative for objective evaluation.
2. LLM output cannot overwrite engine scores or best moves.
3. Expensive work never runs synchronously in an HTTP request.
4. Identical normalized positions should converge on a shared cached engine result.
5. Long-term weakness statements require sample-size-aware confidence.
