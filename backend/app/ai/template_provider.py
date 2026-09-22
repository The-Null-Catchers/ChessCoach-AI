from __future__ import annotations

from app.ai.base import CoachingContext, CoachingExplanation


class TemplateCoachProvider:
    name = "template"
    model = "deterministic-v1"

    def explain(self, context: CoachingContext) -> CoachingExplanation:
        theme = context.semantic_theme.replace("_", " ")
        return CoachingExplanation(
            explanation=f"This move was classified as {context.classification} because it allowed a significant change in the position. The key theme is {theme}.",
            coaching_tip=f"Before committing, check forcing moves and ask whether the move creates or leaves a {theme} problem.",
            concept=theme,
            avoid_next_time="Scan checks, captures, threats, and loose pieces before making the final decision.",
        )
