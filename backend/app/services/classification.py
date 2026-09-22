from dataclasses import dataclass

@dataclass(frozen=True)
class MoveContext:
    before_cp: int | None
    after_cp: int | None
    forced_move_count: int | None = None
    mate_before: int | None = None
    mate_after: int | None = None


def classify_move(ctx: MoveContext) -> tuple[str, int | None]:
    if ctx.mate_before is not None and ctx.mate_after is None and ctx.mate_before > 0:
        return 'blunder', None
    if ctx.before_cp is None or ctx.after_cp is None:
        return 'good', None
    loss = max(0, ctx.before_cp - ctx.after_cp)
    if ctx.forced_move_count == 1:
        loss = int(loss * 0.45)
    advantage = abs(ctx.before_cp)
    if advantage > 600:
        loss = int(loss * 0.7)
    if loss <= 12:
        return 'best', loss
    if loss <= 35:
        return 'excellent', loss
    if loss <= 80:
        return 'good', loss
    if loss <= 150:
        return 'inaccuracy', loss
    if loss <= 300:
        return 'mistake', loss
    return 'blunder', loss
