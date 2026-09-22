from dataclasses import dataclass


@dataclass(frozen=True)
class MoveContext:
    before_cp: int | None
    after_cp: int | None
    forced_move_count: int | None = None
    mate_before: int | None = None
    mate_after: int | None = None


def classify_move(ctx: MoveContext) -> tuple[str, int | None]:
    # Mate scores require their own ordering; centipawn loss is undefined across
    # transitions into/out of forced mate.
    if ctx.mate_after == 0:
        return "best", None

    if ctx.mate_after is not None:
        if ctx.mate_after > 0:
            # The played move preserves or creates a forced mate for the mover.
            return "best", None
        if ctx.mate_after < 0:
            if ctx.mate_before is None or ctx.mate_before >= 0:
                # A normal/winning position became a forced mate against us.
                return "blunder", None
            # Already being mated: shortening the opponent's mate is worse,
            # extending it is at least a useful defensive resource.
            if abs(ctx.mate_after) < abs(ctx.mate_before):
                return "mistake", None
            return "good", None

    if ctx.mate_before is not None:
        if ctx.mate_before > 0:
            # A forced mate was available before the move and is now gone.
            return "blunder", None
        if ctx.mate_before < 0:
            # The move escaped a forced mate.
            return "best", None

    if ctx.before_cp is None or ctx.after_cp is None:
        return "good", None

    loss = max(0, ctx.before_cp - ctx.after_cp)
    if ctx.forced_move_count == 1:
        loss = int(loss * 0.45)
    advantage = abs(ctx.before_cp)
    if advantage > 600:
        loss = int(loss * 0.7)
    if loss <= 12:
        return "best", loss
    if loss <= 35:
        return "excellent", loss
    if loss <= 80:
        return "good", loss
    if loss <= 150:
        return "inaccuracy", loss
    if loss <= 300:
        return "mistake", loss
    return "blunder", loss
