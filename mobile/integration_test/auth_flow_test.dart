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

    final modeToggle = find.byKey(const ValueKey('auth-mode-toggle'));
    expect(modeToggle, findsOneWidget);
    await tester.ensureVisible(modeToggle);
    await tester.pumpAndSettle();
    await tester.tap(modeToggle);
    await tester.pumpAndSettle();

    expect(find.text('Create your coach profile'), findsOneWidget);

    Future<void> fillField(String key, String value) async {
      final field = find.byKey(ValueKey(key));
      expect(field, findsOneWidget);
      await tester.ensureVisible(field);
      await tester.pumpAndSettle();
      await tester.tap(field);
      await tester.enterText(field, value);
    }

    await fillField('auth-display-name', 'Mobile E2E');
    await fillField('auth-email', 'mobile-e2e@example.com');
    await fillField('auth-password', 'e2e-secure-password');

    final submit = find.byKey(const ValueKey('auth-submit'));
    expect(submit, findsOneWidget);
    await tester.ensureVisible(submit);
    await tester.pumpAndSettle();
    await tester.tap(submit);

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
