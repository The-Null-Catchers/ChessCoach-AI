import 'package:chesscoach_mobile/main.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('renders ChessCoach dashboard', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ChessCoachApp()));
    expect(find.text('ChessCoach AI'), findsOneWidget);
    expect(find.text('Start today’s training'), findsOneWidget);
  });
}
