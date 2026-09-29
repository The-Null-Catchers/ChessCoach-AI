import 'dart:math' as math;

import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';

import 'chess_piece_art.dart';

typedef ChessMoveCallback = Future<void> Function(String uci);

class ChessBoardArrow {
  const ChessBoardArrow({
    required this.from,
    required this.to,
    required this.color,
  });

  final String from;
  final String to;
  final Color color;
}

Map<String, String> parseFenPieces(String fen) {
  final boardPart = fen.trim().split(RegExp(r'\s+')).first;
  final ranks = boardPart.split('/');
  if (ranks.length != 8) {
    throw const FormatException('FEN must contain eight ranks');
  }

  final pieces = <String, String>{};
  for (var row = 0; row < 8; row += 1) {
    var file = 0;
    for (final rune in ranks[row].runes) {
      final token = String.fromCharCode(rune);
      final empty = int.tryParse(token);
      if (empty != null) {
        file += empty;
        continue;
      }
      if (file > 7 || !RegExp(r'^[prnbqkPRNBQK]$').hasMatch(token)) {
        throw const FormatException('Invalid FEN board');
      }
      final square =
          String.fromCharCode('a'.codeUnitAt(0) + file) + (8 - row).toString();
      pieces[square] = token;
      file += 1;
    }
    if (file != 8) {
      throw const FormatException('Invalid FEN rank width');
    }
  }
  return pieces;
}

List<String> orientedSquares({required bool whiteAtBottom}) {
  final squares = <String>[];
  final ranks = whiteAtBottom
      ? const <int>[8, 7, 6, 5, 4, 3, 2, 1]
      : const <int>[1, 2, 3, 4, 5, 6, 7, 8];
  final files = whiteAtBottom
      ? const <String>['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
      : const <String>['h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'];
  for (final rank in ranks) {
    for (final file in files) {
      squares.add(file + rank.toString());
    }
  }
  return squares;
}

bool _isWhitePiece(String piece) => piece == piece.toUpperCase();

class ChessPositionBoard extends StatefulWidget {
  const ChessPositionBoard({
    required this.fen,
    this.whiteAtBottom = true,
    this.enabled = false,
    this.lastMoveUci,
    this.arrows = const [],
    this.onMove,
    super.key,
  });

  final String fen;
  final bool whiteAtBottom;
  final bool enabled;
  final String? lastMoveUci;
  final List<ChessBoardArrow> arrows;
  final ChessMoveCallback? onMove;

  @override
  State<ChessPositionBoard> createState() => _ChessPositionBoardState();
}

class _ChessPositionBoardState extends State<ChessPositionBoard>
    with SingleTickerProviderStateMixin {
  late chess.Chess _game;
  String? _selectedSquare;
  Set<String> _legalTargets = const {};
  bool _submitting = false;
  late final AnimationController _moveController;
  String? _moveFrom;
  String? _moveTo;
  String? _movingPiece;
  String? _capturedPiece;

  @override
  void initState() {
    super.initState();
    _moveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 240),
    )..addStatusListener((status) {
        if (status == AnimationStatus.completed && mounted) {
          setState(() {
            _moveFrom = null;
            _moveTo = null;
            _movingPiece = null;
            _capturedPiece = null;
          });
        }
      });
    _loadFen();
  }

  @override
  void dispose() {
    _moveController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant ChessPositionBoard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.fen != widget.fen) {
      _prepareMoveAnimation(oldWidget.fen);
      _loadFen();
    }
  }

  void _prepareMoveAnimation(String previousFen) {
    final lastMove = widget.lastMoveUci;
    if (lastMove == null || lastMove.length < 4) {
      _moveFrom = null;
      _moveTo = null;
      _movingPiece = null;
      _capturedPiece = null;
      return;
    }

    final oldPieces = parseFenPieces(previousFen);
    final from = lastMove.substring(0, 2);
    final to = lastMove.substring(2, 4);
    final piece = oldPieces[from];
    if (piece == null) return;

    _moveFrom = from;
    _moveTo = to;
    _movingPiece = piece;
    _capturedPiece = oldPieces[to];
    _moveController.forward(from: 0);
  }

  void _loadFen() {
    _game = chess.Chess.fromFEN(widget.fen);
    _selectedSquare = null;
    _legalTargets = const {};
    _submitting = false;
  }

  List<chess.Move> _movesFrom(String square) {
    return _game
        .generate_moves()
        .where((move) => move.fromAlgebraic == square)
        .toList(growable: false);
  }

  bool _pieceCanMove(String square, String? piece) {
    if (!widget.enabled || _submitting || piece == null) return false;
    final sideToMove =
        _game.fen.trim().split(RegExp(r'\s+')).elementAt(1) == 'w';
    return _isWhitePiece(piece) == sideToMove && _movesFrom(square).isNotEmpty;
  }

  void _selectSquare(String square, String? piece) {
    if (!_pieceCanMove(square, piece)) {
      if (_legalTargets.contains(square) && _selectedSquare != null) {
        _attemptMove(_selectedSquare!, square);
      } else {
        setState(() {
          _selectedSquare = null;
          _legalTargets = const {};
        });
      }
      return;
    }

    final targets = _movesFrom(square).map((move) => move.toAlgebraic).toSet();
    setState(() {
      _selectedSquare = square;
      _legalTargets = targets;
    });
  }

  Future<String?> _promotionChoice() {
    final sideToMoveIsWhite =
        _game.fen.trim().split(RegExp(r'\\s+')).elementAt(1) == 'w';

    return showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Promote pawn',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 4),
              Text(
                'Choose the piece for your promotion.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  for (final entry in const [
                    ('q', 'Queen'),
                    ('r', 'Rook'),
                    ('b', 'Bishop'),
                    ('n', 'Knight'),
                  ])
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(18),
                          onTap: () => Navigator.of(context).pop(entry.$1),
                          child: Ink(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 4,
                              vertical: 12,
                            ),
                            decoration: BoxDecoration(
                              color: Theme.of(context)
                                  .colorScheme
                                  .surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                ChessPieceArt(
                                  piece: sideToMoveIsWhite
                                      ? entry.$1.toUpperCase()
                                      : entry.$1,
                                  size: 52,
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  entry.$2,
                                  style: Theme.of(context).textTheme.labelMedium,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _attemptMove(String from, String to) async {
    if (_submitting || !_legalTargets.contains(to)) return;
    final candidates = _movesFrom(from)
        .where((move) => move.toAlgebraic == to)
        .toList(growable: false);
    if (candidates.isEmpty) return;

    String? promotion;
    if (candidates.any((move) => move.promotion != null)) {
      promotion = await _promotionChoice();
      if (promotion == null || !mounted) return;
    }

    final moveData = <String, String>{
      'from': from,
      'to': to,
      if (promotion != null) 'promotion': promotion,
    };
    if (!_game.move(moveData)) return;

    final uci = from + to + (promotion ?? '');
    setState(() {
      _selectedSquare = null;
      _legalTargets = const {};
      _submitting = true;
    });

    try {
      await widget.onMove?.call(uci);
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _beginDrag(String square, String? piece) {
    if (!_pieceCanMove(square, piece)) return;
    final targets = _movesFrom(square).map((move) => move.toAlgebraic).toSet();
    setState(() {
      _selectedSquare = square;
      _legalTargets = targets;
    });
  }

  Offset _squareTopLeft(
    String square,
    double cell, {
    required bool whiteAtBottom,
  }) {
    final file = square.codeUnitAt(0) - 'a'.codeUnitAt(0);
    final rank = int.parse(square[1]);
    final col = whiteAtBottom ? file : 7 - file;
    final row = whiteAtBottom ? 8 - rank : rank - 1;
    return Offset(col * cell, row * cell);
  }

  @override
  Widget build(BuildContext context) {
    final pieces = parseFenPieces(_game.fen);
    final squares = orientedSquares(whiteAtBottom: widget.whiteAtBottom);
    final colorScheme = Theme.of(context).colorScheme;
    final darkMode = Theme.of(context).brightness == Brightness.dark;
    final lightSquare = darkMode
        ? colorScheme.surfaceContainerHighest
        : const Color(0xFFE9EDCC);
    final darkSquare =
        darkMode ? const Color(0xFF52634A) : const Color(0xFF769656);
    final selectedColor = colorScheme.primary.withValues(alpha: 0.42);
    final lastMoveColor = colorScheme.tertiary.withValues(alpha: 0.36);

    return LayoutBuilder(
      builder: (context, constraints) {
        final available = math.min(
          constraints.maxWidth,
          constraints.maxHeight.isFinite
              ? constraints.maxHeight
              : constraints.maxWidth,
        );
        final size = available.isFinite ? available : constraints.maxWidth;
        final squareSize = size / 8;

        return Center(
          child: SizedBox.square(
            dimension: size,
            child: Stack(
              children: [
                GridView.builder(
                  physics: const NeverScrollableScrollPhysics(),
                  padding: EdgeInsets.zero,
                  itemCount: 64,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 8,
                  ),
                  itemBuilder: (context, index) {
                    final square = squares[index];
                    final file = square.codeUnitAt(0) - 'a'.codeUnitAt(0);
                    final rank = int.parse(square[1]);
                    final isLight = (file + rank).isEven;
                    final piece = pieces[square];
                    final lastMove = widget.lastMoveUci;
                    final isLastMove = lastMove != null &&
                        lastMove.length >= 4 &&
                        (lastMove.substring(0, 2) == square ||
                            lastMove.substring(2, 4) == square);
                    final selected = square == _selectedSquare;
                    final legal = _legalTargets.contains(square);
                    final canDrag = _pieceCanMove(square, piece);

                    final hideForMove = _moveController.isAnimating &&
                        square == _moveTo &&
                        _movingPiece != null;
                    final pieceWidget = Semantics(
                      label: piece == null ? square : '$square $piece',
                      child: Center(
                        child: piece == null || hideForMove
                            ? const SizedBox.shrink()
                            : ChessPieceArt(
                                key: ValueKey<String>(
                                  "$square-$piece",
                                ),
                                piece: piece,
                                size: squareSize * 0.88,
                                selected: selected,
                              ),
                      ),
                    );

                    return DragTarget<String>(
                      onWillAcceptWithDetails: (_) => legal && !_submitting,
                      onAcceptWithDetails: (details) {
                        _attemptMove(details.data, square);
                      },
                      builder: (context, candidateData, rejectedData) {
                        return GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: widget.enabled
                              ? () => _selectSquare(square, piece)
                              : null,
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 140),
                            curve: Curves.easeOutCubic,
                            color: selected
                                ? selectedColor
                                : isLastMove
                                    ? lastMoveColor
                                    : isLight
                                        ? lightSquare
                                        : darkSquare,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                if (canDrag)
                                  Draggable<String>(
                                    data: square,
                                    onDragStarted: () =>
                                        _beginDrag(square, piece),
                                    feedback: Material(
                                      color: Colors.transparent,
                                      child: SizedBox.square(
                                        dimension: squareSize,
                                        child: pieceWidget,
                                      ),
                                    ),
                                    childWhenDragging: Opacity(
                                      opacity: 0.25,
                                      child: pieceWidget,
                                    ),
                                    child: pieceWidget,
                                  )
                                else
                                  pieceWidget,
                                if (selected)
                                  Center(
                                    child: IgnorePointer(
                                      child: Container(
                                        width: squareSize * 0.84,
                                        height: squareSize * 0.84,
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            width: math.max(
                                              2,
                                              squareSize * 0.045,
                                            ),
                                            color: colorScheme.onPrimary
                                                .withValues(alpha: 0.5),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                if (legal)
                                  Center(
                                    child: TweenAnimationBuilder<double>(
                                      duration: const Duration(milliseconds: 150),
                                      tween: Tween(begin: 0.7, end: 1),
                                      curve: Curves.easeOutBack,
                                      builder: (context, scale, child) {
                                        return Transform.scale(
                                          scale: scale,
                                          child: child,
                                        );
                                      },
                                      child: Container(
                                        width: piece == null
                                            ? squareSize * 0.22
                                            : squareSize * 0.82,
                                        height: piece == null
                                            ? squareSize * 0.22
                                            : squareSize * 0.82,
                                        decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: piece == null
                                            ? colorScheme.onSurface
                                                .withValues(alpha: 0.23)
                                            : Colors.transparent,
                                        border: piece == null
                                            ? null
                                            : Border.all(
                                                width: squareSize * 0.07,
                                                color: colorScheme.onSurface
                                                    .withValues(alpha: 0.22),
                                              ),
                                        ),
                                      ),
                                    ),
                                  ),
                                if (index % 8 == 0)
                                  Positioned(
                                    left: 2,
                                    top: 1,
                                    child: Text(
                                      square[1],
                                      style: TextStyle(
                                        fontSize:
                                            math.max(8, squareSize * 0.13),
                                        fontWeight: FontWeight.w700,
                                        color: isLight
                                            ? darkSquare
                                            : lightSquare,
                                      ),
                                    ),
                                  ),
                                if (index ~/ 8 == 7)
                                  Positioned(
                                    right: 2,
                                    bottom: 1,
                                    child: Text(
                                      square[0],
                                      style: TextStyle(
                                        fontSize:
                                            math.max(8, squareSize * 0.13),
                                        fontWeight: FontWeight.w700,
                                        color: isLight
                                            ? darkSquare
                                            : lightSquare,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
                if (_capturedPiece != null &&
                    _moveTo != null &&
                    _moveController.isAnimating)
                  AnimatedBuilder(
                    animation: _moveController,
                    builder: (context, child) {
                      final target = _squareTopLeft(
                        _moveTo!,
                        squareSize,
                        whiteAtBottom: widget.whiteAtBottom,
                      );
                      final t = Curves.easeOut.transform(
                        _moveController.value,
                      );
                      return Positioned(
                        left: target.dx,
                        top: target.dy,
                        width: squareSize,
                        height: squareSize,
                        child: IgnorePointer(
                          child: Opacity(
                            opacity: 1 - t,
                            child: Transform.scale(
                              scale: 1 - (0.18 * t),
                              child: Center(
                                child: ChessPieceArt(
                                  piece: _capturedPiece!,
                                  size: squareSize * 0.88,
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                if (_movingPiece != null &&
                    _moveFrom != null &&
                    _moveTo != null &&
                    _moveController.isAnimating)
                  AnimatedBuilder(
                    animation: _moveController,
                    builder: (context, child) {
                      final from = _squareTopLeft(
                        _moveFrom!,
                        squareSize,
                        whiteAtBottom: widget.whiteAtBottom,
                      );
                      final to = _squareTopLeft(
                        _moveTo!,
                        squareSize,
                        whiteAtBottom: widget.whiteAtBottom,
                      );
                      final t = Curves.easeInOutCubic.transform(
                        _moveController.value,
                      );
                      final offset = Offset.lerp(from, to, t)!;
                      final lift = 1 + (0.08 * math.sin(math.pi * t));
                      return Positioned(
                        left: offset.dx,
                        top: offset.dy,
                        width: squareSize,
                        height: squareSize,
                        child: IgnorePointer(
                          child: Transform.scale(
                            scale: lift,
                            child: Center(
                              child: ChessPieceArt(
                                piece: _movingPiece!,
                                size: squareSize * 0.9,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                IgnorePointer(
                  child: CustomPaint(
                    size: Size.square(size),
                    painter: _ArrowPainter(
                      arrows: widget.arrows,
                      whiteAtBottom: widget.whiteAtBottom,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ArrowPainter extends CustomPainter {
  const _ArrowPainter({
    required this.arrows,
    required this.whiteAtBottom,
  });

  final List<ChessBoardArrow> arrows;
  final bool whiteAtBottom;

  Offset _center(String square, Size size) {
    final file = square.codeUnitAt(0) - 'a'.codeUnitAt(0);
    final rank = int.parse(square[1]);
    final col = whiteAtBottom ? file : 7 - file;
    final row = whiteAtBottom ? 8 - rank : rank - 1;
    final cell = size.width / 8;
    return Offset((col + 0.5) * cell, (row + 0.5) * cell);
  }

  @override
  void paint(Canvas canvas, Size size) {
    for (final arrow in arrows) {
      if (arrow.from.length != 2 || arrow.to.length != 2) continue;
      final start = _center(arrow.from, size);
      final end = _center(arrow.to, size);
      final vector = end - start;
      if (vector.distance < 1) continue;

      final unit = vector / vector.distance;
      final cell = size.width / 8;
      final headLength = cell * 0.32;
      final shaftEnd = end - unit * headLength * 0.55;
      final normal = Offset(-unit.dy, unit.dx);
      final paint = Paint()
        ..color = arrow.color.withValues(alpha: 0.74)
        ..strokeWidth = cell * 0.12
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;

      canvas.drawLine(start, shaftEnd, paint);

      final path = Path()
        ..moveTo(end.dx, end.dy)
        ..lineTo(
          end.dx - unit.dx * headLength + normal.dx * headLength * 0.42,
          end.dy - unit.dy * headLength + normal.dy * headLength * 0.42,
        )
        ..lineTo(
          end.dx - unit.dx * headLength - normal.dx * headLength * 0.42,
          end.dy - unit.dy * headLength - normal.dy * headLength * 0.42,
        )
        ..close();
      canvas.drawPath(
        path,
        Paint()
          ..color = arrow.color.withValues(alpha: 0.74)
          ..style = PaintingStyle.fill,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _ArrowPainter oldDelegate) {
    return oldDelegate.arrows != arrows ||
        oldDelegate.whiteAtBottom != whiteAtBottom;
  }
}
