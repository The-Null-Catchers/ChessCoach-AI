import 'package:flutter/material.dart';

class ChessPieceArt extends StatelessWidget {
  const ChessPieceArt({
    required this.piece,
    required this.size,
    this.selected = false,
    super.key,
  });

  final String piece;
  final double size;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AnimatedScale(
        scale: selected ? 1.05 : 1,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOutCubic,
        child: CustomPaint(
          size: Size.square(size),
          painter: _ChessPiecePainter(piece),
        ),
      ),
    );
  }
}

class _ChessPiecePainter extends CustomPainter {
  const _ChessPiecePainter(this.piece);

  final String piece;

  bool get _white => piece == piece.toUpperCase();
  String get _kind => piece.toLowerCase();

  @override
  void paint(Canvas canvas, Size size) {
    if (piece.isEmpty) return;

    final scale = size.shortestSide / 100;
    canvas.save();
    canvas.scale(scale, scale);

    final path = _piecePath(_kind);
    final bounds = path.getBounds();

    final shadowColor =
        _white ? const Color(0x55000000) : const Color(0x88000000);
    canvas.drawShadow(path, shadowColor, 3.2, false);

    final fill = Paint()
      ..style = PaintingStyle.fill
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: _white
            ? const [
                Color(0xFFFFFDF5),
                Color(0xFFE8E4D6),
                Color(0xFFC9C4B5),
              ]
            : const [
                Color(0xFF414740),
                Color(0xFF1D211D),
                Color(0xFF090B09),
              ],
        stops: const [0, 0.58, 1],
      ).createShader(bounds);

    final outline = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.7
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round
      ..color = _white ? const Color(0xFF53574F) : const Color(0xFF050605);

    canvas.drawPath(path, fill);
    canvas.drawPath(path, outline);

    _paintDetails(canvas);

    canvas.restore();
  }

  Path _piecePath(String kind) {
    switch (kind) {
      case 'p':
        return _pawn();
      case 'r':
        return _rook();
      case 'n':
        return _knight();
      case 'b':
        return _bishop();
      case 'q':
        return _queen();
      case 'k':
        return _king();
      default:
        return Path();
    }
  }

  Path _base({
    double left = 19,
    double right = 81,
    double top = 67,
  }) {
    return Path()
      ..moveTo(27, top)
      ..quadraticBezierTo(24, 75, left, 82)
      ..quadraticBezierTo(17, 88, 25, 91)
      ..lineTo(75, 91)
      ..quadraticBezierTo(83, 88, right, 82)
      ..quadraticBezierTo(76, 75, 73, top)
      ..close();
  }

  Path _pawn() {
    final p = Path();
    p.addOval(Rect.fromCircle(center: const Offset(50, 25), radius: 13));
    p.addPath(
      Path()
        ..moveTo(43, 38)
        ..quadraticBezierTo(34, 46, 35, 58)
        ..quadraticBezierTo(36, 65, 30, 70)
        ..lineTo(70, 70)
        ..quadraticBezierTo(64, 65, 65, 58)
        ..quadraticBezierTo(66, 46, 57, 38)
        ..close(),
      Offset.zero,
    );
    p.addPath(_base(top: 67), Offset.zero);
    return p;
  }

  Path _rook() {
    final p = Path()
      ..moveTo(22, 17)
      ..lineTo(22, 32)
      ..lineTo(28, 32)
      ..lineTo(31, 64)
      ..lineTo(25, 70)
      ..lineTo(75, 70)
      ..lineTo(69, 64)
      ..lineTo(72, 32)
      ..lineTo(78, 32)
      ..lineTo(78, 17)
      ..lineTo(66, 17)
      ..lineTo(66, 25)
      ..lineTo(57, 25)
      ..lineTo(57, 17)
      ..lineTo(43, 17)
      ..lineTo(43, 25)
      ..lineTo(34, 25)
      ..lineTo(34, 17)
      ..close();
    p.addPath(_base(top: 67), Offset.zero);
    return p;
  }

  Path _bishop() {
    final p = Path()
      ..moveTo(50, 12)
      ..quadraticBezierTo(36, 21, 36, 35)
      ..quadraticBezierTo(36, 43, 43, 49)
      ..quadraticBezierTo(34, 56, 32, 69)
      ..lineTo(68, 69)
      ..quadraticBezierTo(66, 56, 57, 49)
      ..quadraticBezierTo(64, 43, 64, 35)
      ..quadraticBezierTo(64, 21, 50, 12)
      ..close();
    p.addPath(_base(top: 67), Offset.zero);
    return p;
  }

  Path _knight() {
    final p = Path()
      ..moveTo(30, 69)
      ..quadraticBezierTo(31, 58, 38, 51)
      ..quadraticBezierTo(43, 46, 43, 38)
      ..lineTo(34, 42)
      ..quadraticBezierTo(29, 44, 27, 39)
      ..quadraticBezierTo(26, 36, 30, 32)
      ..lineTo(44, 17)
      ..quadraticBezierTo(48, 12, 55, 14)
      ..quadraticBezierTo(67, 18, 72, 29)
      ..quadraticBezierTo(77, 40, 70, 50)
      ..quadraticBezierTo(66, 56, 63, 69)
      ..close();
    p.addPath(_base(top: 67), Offset.zero);
    return p;
  }

  Path _queen() {
    final p = Path()
      ..moveTo(23, 30)
      ..lineTo(31, 59)
      ..quadraticBezierTo(35, 65, 31, 70)
      ..lineTo(69, 70)
      ..quadraticBezierTo(65, 65, 69, 59)
      ..lineTo(77, 30)
      ..lineTo(63, 47)
      ..lineTo(56, 25)
      ..lineTo(50, 48)
      ..lineTo(44, 25)
      ..lineTo(37, 47)
      ..close();
    p.addPath(_base(top: 67), Offset.zero);
    p.addOval(Rect.fromCircle(center: const Offset(23, 25), radius: 5));
    p.addOval(Rect.fromCircle(center: const Offset(44, 20), radius: 5));
    p.addOval(Rect.fromCircle(center: const Offset(56, 20), radius: 5));
    p.addOval(Rect.fromCircle(center: const Offset(77, 25), radius: 5));
    return p;
  }

  Path _king() {
    final p = Path()
      ..moveTo(44, 26)
      ..lineTo(56, 26)
      ..lineTo(56, 38)
      ..quadraticBezierTo(67, 44, 65, 56)
      ..quadraticBezierTo(64, 63, 69, 69)
      ..lineTo(31, 69)
      ..quadraticBezierTo(36, 63, 35, 56)
      ..quadraticBezierTo(33, 44, 44, 38)
      ..close();
    p.addPath(_base(top: 67), Offset.zero);
    p.addPath(
      Path()
        ..moveTo(47, 8)
        ..lineTo(53, 8)
        ..lineTo(53, 15)
        ..lineTo(61, 15)
        ..lineTo(61, 21)
        ..lineTo(53, 21)
        ..lineTo(53, 29)
        ..lineTo(47, 29)
        ..lineTo(47, 21)
        ..lineTo(39, 21)
        ..lineTo(39, 15)
        ..lineTo(47, 15)
        ..close(),
      Offset.zero,
    );
    return p;
  }

  void _paintDetails(Canvas canvas) {
    final detail = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = _white ? const Color(0xFF8E9188) : const Color(0xFF666D64);

    switch (_kind) {
      case 'b':
        canvas.drawLine(const Offset(45, 20), const Offset(55, 36), detail);
        break;
      case 'n':
        final eye = Paint()
          ..style = PaintingStyle.fill
          ..color = _white ? const Color(0xFF2B2E2A) : const Color(0xFFD1D5C9);
        canvas.drawCircle(const Offset(57, 29), 2.2, eye);
        canvas.drawPath(
          Path()
            ..moveTo(43, 38)
            ..quadraticBezierTo(51, 40, 58, 46),
          detail,
        );
        break;
      case 'r':
        canvas.drawLine(const Offset(30, 36), const Offset(70, 36), detail);
        break;
      case 'q':
        canvas.drawLine(const Offset(34, 57), const Offset(66, 57), detail);
        break;
      case 'k':
        canvas.drawLine(const Offset(40, 49), const Offset(60, 49), detail);
        break;
      case 'p':
        canvas.drawLine(const Offset(37, 58), const Offset(63, 58), detail);
        break;
    }
  }

  @override
  bool shouldRepaint(covariant _ChessPiecePainter oldDelegate) {
    return oldDelegate.piece != piece;
  }
}
