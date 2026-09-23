import 'package:chesscoach_mobile/widgets/chess_board.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('FEN board parsing', () {
    test('parses the initial chess position', () {
      const fen =
          'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
      final pieces = parseFenPieces(fen);

      expect(pieces.length, 32);
      expect(pieces['a8'], 'r');
      expect(pieces['e8'], 'k');
      expect(pieces['a7'], 'p');
      expect(pieces['e2'], 'P');
      expect(pieces['e1'], 'K');
      expect(pieces['h1'], 'R');
    });

    test('parses sparse puzzle positions', () {
      final pieces = parseFenPieces(
        '8/8/8/3k4/8/4K3/3P4/8 w - - 0 1',
      );

      expect(pieces, {
        'd5': 'k',
        'e3': 'K',
        'd2': 'P',
      });
    });

    test('rejects malformed board ranks', () {
      expect(
        () => parseFenPieces('8/8/8/8/8/8/8 w - - 0 1'),
        throwsFormatException,
      );
      expect(
        () => parseFenPieces('9/8/8/8/8/8/8/8 w - - 0 1'),
        throwsFormatException,
      );
    });
  });

  group('board orientation', () {
    test('white orientation maps a8 to top-left and h1 to bottom-right', () {
      final squares = orientedSquares(whiteAtBottom: true);

      expect(squares.first, 'a8');
      expect(squares[7], 'h8');
      expect(squares[56], 'a1');
      expect(squares.last, 'h1');
    });

    test('black orientation mirrors files and ranks', () {
      final squares = orientedSquares(whiteAtBottom: false);

      expect(squares.first, 'h1');
      expect(squares[7], 'a1');
      expect(squares[56], 'h8');
      expect(squares.last, 'a8');
    });
  });
}
