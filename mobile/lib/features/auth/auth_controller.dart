import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../core/api_client.dart';

class AuthState {
  const AuthState({
    required this.loading,
    required this.signedIn,
    this.error,
  });

  const AuthState.loading() : this(loading: true, signedIn: false);
  const AuthState.signedOut({String? error})
      : this(loading: false, signedIn: false, error: error);
  const AuthState.signedIn()
      : this(loading: false, signedIn: true);

  final bool loading;
  final bool signedIn;
  final String? error;
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this.api) : super(const AuthState.loading()) {
    _bootstrap();
  }

  final ChessCoachApi api;

  Future<void> _bootstrap() async {
    try {
      await api.initialize();
      state = api.isSignedIn
          ? const AuthState.signedIn()
          : const AuthState.signedOut();
    } catch (_) {
      state = const AuthState.signedOut(
        error: 'Unable to read the saved session.',
      );
    }
  }

  Future<void> login(String email, String password) async {
    state = const AuthState.loading();
    try {
      await api.login(email, password);
      state = const AuthState.signedIn();
    } catch (_) {
      state = const AuthState.signedOut(
        error: 'Sign in failed. Check your credentials and connection.',
      );
    }
  }

  Future<void> register(
    String email,
    String password,
    String? displayName,
  ) async {
    state = const AuthState.loading();
    try {
      await api.register(email, password, displayName);
      state = const AuthState.signedIn();
    } catch (_) {
      state = const AuthState.signedOut(
        error: 'Registration failed. Check the form and try again.',
      );
    }
  }

  Future<void> logout() async {
    state = const AuthState.loading();
    await api.logout();
    state = const AuthState.signedOut();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(ref.watch(apiClientProvider));
});
