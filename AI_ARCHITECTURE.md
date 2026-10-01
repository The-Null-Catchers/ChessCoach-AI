# AI Architecture

ChessCoach AI separates objective chess calculation from pedagogical explanation.

## Sources of truth

- **Stockfish** owns objective evaluation, mate scores, best moves and candidate variations.
- **Deterministic chess detectors** identify explainable tactical, positional and time-management themes.
- **The AI coach** turns engine facts and detected concepts into level-appropriate language. It cannot overwrite engine facts.

## Provider contract

Providers implement the typed `AIProvider` contract in `backend/app/ai/base.py`. The current runtime supports:

- deterministic template fallback for local/offline-safe operation
- OpenAI-compatible HTTP providers through configurable provider name, model, base URL and API key

This makes OpenAI-compatible endpoints such as hosted OpenAI-style APIs, Groq-compatible gateways and local OpenAI-compatible inference interchangeable without changing coaching code. Provider-specific adapters can be added behind the same interface when a vendor requires a different protocol.

## Structured coaching

A coaching request contains:

- player skill band
- FEN
- move played
- engine best move
- move classification and centipawn loss
- semantic theme
- engine principal variation

Responses are schema-validated into:

- explanation
- coaching tip
- concept
- how to avoid the mistake next time

If the configured provider fails validation or transport, ChessCoach falls back to the deterministic coach rather than blocking analysis completion.

## Cost control

LLM work is intentionally limited to the most important persisted mistakes. Explanations are cached by move, prompt version and skill band, so repeated reads do not trigger new model calls. Stockfish analysis and deterministic detectors run independently of the LLM.

## Analysis profiles and candidate lines

Engine workers support quick, normal and deep profiles. Profiles control depth and MultiPV count. Candidate lines are cached by normalized position, engine, depth and MultiPV setting, then persisted on move analysis for explainable game review.

## Prompt evolution

The current prompt version is stored with every AI explanation. Prompt changes should increment the version so old and new explanations can coexist and be audited. Prompt text should move into dedicated versioned templates as the coaching surface grows.
