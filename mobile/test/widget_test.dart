import 'package:chesscoach_mobile/app_providers.dart';
import 'package:chesscoach_mobile/core/api_client.dart';
import 'package:chesscoach_mobile/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeApi implements ChessCoachApi {
  @override
  bool get isSignedIn => false;

  @override
  Future<void> initialize() async {}

  @override
  Future<void> login(String email, String password) async {}

  @override
  Future<void> register(
    String email,
    String password,
    String? displayName,
  ) async {}

  @override
  Future<void> logout() async {}

  @override
  Future<dynamic> cachedGet(String path, {required String cacheKey}) async {
    return <String, dynamic>{};
  }

  @override
  Future<dynamic> getJson(String path) async => <String, dynamic>{};

  @override
  Future<dynamic> postJson(
    String path, {
    Map<String, dynamic>? data,
  }) async =>
      <String, dynamic>{};

  @override
  Future<Map<String, dynamic>> submitPuzzleAttempt(
    String puzzleId,
    String moveUci, {
    int? durationSeconds,
  }) async =>
      <String, dynamic>{};

  @override
  Future<int> syncPendingPuzzleAttempts() async => 0;
}

void main() {
  testWidgets('shows authentication before coaching data', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(_FakeApi()),
        ],
        child: const ChessCoachApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('CHESSCOACH AI'), findsOneWidget);
    expect(find.text('Welcome back'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });
}
