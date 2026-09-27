import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:chesscoach_mobile/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('registers against the real API and opens the games tab',
      (tester) async {
    await app.main();
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);
    await tester.tap(find.text('Need an account? Register'));
    await tester.pumpAndSettle();

    Future<void> fillField(String label, String value) async {
      final field = find.byWidgetPredicate(
        (widget) =>
            widget is TextField &&
            widget.decoration?.labelText == label,
      );
      expect(field, findsOneWidget);
      await tester.ensureVisible(field);
      await tester.pumpAndSettle();
      await tester.tap(field);
      await tester.enterText(field, value);
    }

    await fillField('Display name', 'Mobile E2E');
    await fillField('Email', 'mobile-e2e@example.com');
    await fillField('Password', 'e2e-secure-password');

    final createAccount = find.text('Create account');
    await tester.ensureVisible(createAccount);
    await tester.pumpAndSettle();
    await tester.tap(createAccount);

    final deadline = DateTime.now().add(const Duration(seconds: 30));
    while (find.text('ChessCoach AI').evaluate().isEmpty &&
        DateTime.now().isBefore(deadline)) {
      await tester.pump(const Duration(milliseconds: 500));
    }
    if (find.text('ChessCoach AI').evaluate().isEmpty) {
      final visibleText = find
          .byType(Text)
          .evaluate()
          .map((element) => (element.widget as Text).data)
          .whereType<String>()
          .join(' | ');
      fail(
        'Registration did not reach the authenticated shell. '
        'Visible text: $visibleText',
      );
    }

    expect(find.text('ChessCoach AI'), findsOneWidget);
    expect(find.text('Coach'), findsWidgets);

    final games = find.text('Games').last;
    await tester.ensureVisible(games);
    await tester.tap(games);
    await tester.pumpAndSettle(const Duration(seconds: 3));

    expect(
      find.text(
        'No games yet. Import PGN games from the web client to start building your coaching history.',
      ),
      findsOneWidget,
    );

    final signOut = find.byTooltip('Sign out');
    expect(signOut, findsOneWidget);
    await tester.tap(signOut);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.text('Welcome back'), findsOneWidget);
  });
}
