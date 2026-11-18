# ChessCoach-AI portfolio roadmap

Baseline reviewed on November 17, 2026. Repository roadmap published on November 18, 2026.

This roadmap applies to this repository and follows the shared Null Catchers portfolio plan. Verify the documented state against the current code and runs before starting work.

**Estimated initial demo effort** 12–20 hours for a developer familiar with the project. The estimate excludes external reviews, store accounts, target environment setup, and later milestones.

## Project priorities

**Documented state** The app supports Stockfish analysis, PGN import, game review, personal puzzles, and training plans on web and Flutter. The repository documents how to capture demo evidence.

**P0 — Demo** Recapture a game review after the forced-mate display and accuracy fixes. Produce a short, versioned walkthrough.

**P1 — Validation and depth** Show how a mistake becomes a puzzle and changes the training plan. Time analysis of a fixed PGN and identify which outputs come from Stockfish, the explanation provider, or its fallback. Label seeded progress.

**P2 — Later** Improve onboarding and import providers based on demo feedback before adding training sections.

**Acceptance criteria** The evidence identifies the revision. Engine analysis is reproducible, solving the puzzle saves progress, and explanation provider failures leave the Stockfish result intact.

**Demo scenario** Import a game → inspect a critical mistake and the best line → solve a personal puzzle → review the training update. [README](https://github.com/The-Null-Catchers/ChessCoach-AI/blob/main/README.md), [Portfolio Evidence](https://github.com/The-Null-Catchers/ChessCoach-AI/blob/main/PORTFOLIO_EVIDENCE.md).

## Next milestones

[PR #44](https://github.com/The-Null-Catchers/ChessCoach-AI/pull/44) captured real Stockfish analysis. [PR #47](https://github.com/The-Null-Catchers/ChessCoach-AI/pull/47) closed [issue #45](https://github.com/The-Null-Catchers/ChessCoach-AI/issues/45) with forced-mate and accuracy fixes and tests for terminal positions and missing scores.

1. [ ] Use a fixed PGN with forced mate and a mistake that can become a puzzle. Confirm that review shows the mate and best line and that analysis reruns from the release.
2. [ ] Solve the resulting puzzle, verify that progress persists across reopening, and identify newly generated results and seeded data in the demo.
3. [ ] Record 60–120 seconds and capture fresh screenshots. Add the SHA, PGN, reproduction steps, and engine verification to the [evidence index](PORTFOLIO_EVIDENCE.md).

## Portfolio acceptance checklist

- [ ] Another person can reproduce the primary workflow from a clean checkout using the README and test credentials or fixtures.
- [ ] The demo tells one complete story with a defined user, problem, and saved result.
- [ ] Tests cover the main flow, an important failure, and access boundaries when multiple accounts are involved.
- [ ] Demo data is labeled synthetic and reproducible. Review screenshots and recordings for secrets and customer data.
- [ ] Include four to six real screenshots where appropriate, a 60–120 second recording, and working links. Identify the revision used for capture.
- [ ] The README describes implemented capabilities, setup, architecture, limits, tests, and the demo.
- [ ] A short case study explains two engineering decisions, a considered alternative, and how the system handles an actual failure.
- [ ] Release evidence records the commit SHA, CI, prerequisites, and limits. Performance data includes workload, hardware, and method.
- [ ] Licensing and contributor attribution are settled before distribution. Choose the license for each repository individually.

A hosted demo is optional. Code execution, server administration, and secret management can be demonstrated through a recording and a reproducible isolated environment. Keep public demo access scoped to the activities it needs.

## Implementation and follow-up

- Break P0 into tasks with expected behavior, acceptance criteria, and a suitable test.
- Verify existing functionality first. Update this plan when evidence tied to a commit or PR closes a milestone.
- Record the fixture source, the revision used for evidence, and the tested limits.
- Review the final diff and verify required checks for its exact SHA before merging. Follow branch protection.
- For documentation-only changes with no applicable workflow, verify content and links and record the checks actually performed.
- Tie performance, security, and readiness claims to supporting evidence.
