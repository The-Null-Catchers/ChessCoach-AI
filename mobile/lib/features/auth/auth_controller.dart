import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../core/api_client.dart';

class AuthState {
  const AuthState({
    required this.loading,
    required this.signedIn,
    required this.bootstrapping,
    this.error,
  });

  const AuthState.bootstrapping()
      : this(loading: true, signedIn: false, bootstrapping: true);
  const AuthState.submitting()
      : this(loading: true, signedIn: false, bootstrapping: false);
  const AuthState.signedOut({String? error})
      : this(loading: false, signedIn: false, bootstrapping: false, error: error);
  const AuthState.signedIn()
      : this(loading: false, signedIn: true, bootstrapping: false);

  final bool loading;
  final bool signedIn;
  final bool bootstrapping;
  final String? error;
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this.api) : super(const AuthState.bootstrapping()) {
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

  String _authError(Object error, String fallback) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] is String) {
        return data['detail'] as String;
      }
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.receiveTimeout ||
          error.type == DioExceptionType.sendTimeout) {
        return 'Could not reach ChessCoach API. Check your connection and app build.';
      }
    }
    return fallback;
  }

  Future<void> login(String email, String password) async {
    state = const AuthState.submitting();
    try {
      await api.login(email, password);
      state = const AuthState.signedIn();
    } catch (error) {
      state = AuthState.signedOut(
        error: _authError(
          error,
          'Sign in failed. Check your credentials and connection.',
        ),
      );
    }
  }

  Future<void> register(
    String email,
    String password,
    String? displayName,
  ) async {
    state = const AuthState.submitting();
    try {
      await api.register(email, password, displayName);
      state = const AuthState.signedIn();
    } catch (error) {
      state = AuthState.signedOut(
        error: _authError(
          error,
          'Registration failed. Check the form and try again.',
        ),
      );
    }
  }

  Future<void> logout() async {
    state = const AuthState.submitting();
    await api.logout();
    state = const AuthState.signedOut();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(ref.watch(apiClientProvider));
});
