import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract class ChessCoachApi {
  Future<void> initialize();
  bool get isSignedIn;
  Future<void> login(String email, String password);
  Future<void> register(String email, String password, String? displayName);
  Future<void> logout();
  Future<dynamic> cachedGet(String path, {required String cacheKey});
  Future<dynamic> getJson(String path);
  Future<dynamic> postJson(String path, {Map<String, dynamic>? data});
  Future<Map<String, dynamic>> submitPuzzleAttempt(
    String puzzleId,
    String moveUci, {
    int? durationSeconds,
  });
  Future<int> syncPendingPuzzleAttempts();
}

class ApiClient implements ChessCoachApi {
  ApiClient({
    required this.preferences,
    required this.secureStorage,
    String? baseUrl,
  }) {
    final resolvedBaseUrl = baseUrl ??
        const String.fromEnvironment(
          'API_URL',
          defaultValue: 'http://10.0.2.2:8000/api/v1',
        );
    _plain = Dio(BaseOptions(
      baseUrl: resolvedBaseUrl,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 20),
      headers: const {'Accept': 'application/json'},
    ));
    _dio = Dio(BaseOptions(
      baseUrl: resolvedBaseUrl,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 20),
      headers: const {'Accept': 'application/json'},
    ));
    _dio.interceptors.add(QueuedInterceptorsWrapper(
      onRequest: (options, handler) {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final request = error.requestOptions;
        final canRefresh = error.response?.statusCode == 401 &&
            request.extra['retried'] != true &&
            !request.path.startsWith('/auth/');
        if (!canRefresh || !await _refreshTokens()) {
          handler.next(error);
          return;
        }
        request.extra['retried'] = true;
        request.headers['Authorization'] = 'Bearer $_accessToken';
        try {
          final response = await _dio.fetch<dynamic>(request);
          handler.resolve(response);
        } on DioException catch (retryError) {
          handler.next(retryError);
        }
      },
    ));
  }

  static const _accessKey = 'chesscoach_access_token';
  static const _refreshKey = 'chesscoach_refresh_token';
  static const _pendingAttemptsKey = 'chesscoach_pending_puzzle_attempts';

  final SharedPreferences preferences;
  final FlutterSecureStorage secureStorage;
  late final Dio _dio;
  late final Dio _plain;

  String? _accessToken;
  String? _refreshToken;

  @override
  bool get isSignedIn => _accessToken != null && _refreshToken != null;

  @override
  Future<void> initialize() async {
    _accessToken = await secureStorage.read(key: _accessKey);
    _refreshToken = await secureStorage.read(key: _refreshKey);
  }

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    final access = data['access_token'] as String?;
    final refresh = data['refresh_token'] as String?;
    if (access == null || refresh == null) {
      throw StateError('Authentication response did not contain both tokens');
    }
    _accessToken = access;
    _refreshToken = refresh;
    await Future.wait([
      secureStorage.write(key: _accessKey, value: access),
      secureStorage.write(key: _refreshKey, value: refresh),
    ]);
  }

  Future<void> _clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    await Future.wait([
      secureStorage.delete(key: _accessKey),
      secureStorage.delete(key: _refreshKey),
    ]);
  }

  @override
  Future<void> login(String email, String password) async {
    final response = await _plain.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email.trim(), 'password': password},
    );
    await _saveTokens(response.data ?? const {});
  }

  @override
  Future<void> register(String email, String password, String? displayName) async {
    final response = await _plain.post<Map<String, dynamic>>(
      '/auth/register',
      data: {
        'email': email.trim(),
        'password': password,
        if (displayName != null && displayName.trim().isNotEmpty)
          'display_name': displayName.trim(),
      },
    );
    await _saveTokens(response.data ?? const {});
  }

  Future<bool> _refreshTokens() async {
    final refresh = _refreshToken;
    if (refresh == null) return false;
    try {
      final response = await _plain.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refresh},
      );
      await _saveTokens(response.data ?? const {});
      return true;
    } on DioException {
      await _clearTokens();
      return false;
    }
  }

  @override
  Future<void> logout() async {
    final refresh = _refreshToken;
    if (refresh != null) {
      try {
        await _plain.post<dynamic>(
          '/auth/logout',
          data: {'refresh_token': refresh},
        );
      } on DioException {
        // Local logout must still succeed when the device is offline.
      }
    }
    await _clearTokens();
  }

  @override
  Future<dynamic> getJson(String path) async {
    final response = await _dio.get<dynamic>(path);
    return response.data;
  }

  @override
  Future<dynamic> postJson(String path, {Map<String, dynamic>? data}) async {
    final response = await _dio.post<dynamic>(path, data: data);
    return response.data;
  }

  @override
  Future<dynamic> cachedGet(String path, {required String cacheKey}) async {
    try {
      final data = await getJson(path);
      await preferences.setString(cacheKey, jsonEncode(data));
      return data;
    } on DioException catch (error) {
      final cached = preferences.getString(cacheKey);
      if (_isConnectivityFailure(error) && cached != null) {
        return jsonDecode(cached);
      }
      rethrow;
    }
  }

  bool _isConnectivityFailure(DioException error) {
    return switch (error.type) {
      DioExceptionType.connectionError ||
      DioExceptionType.connectionTimeout ||
      DioExceptionType.receiveTimeout ||
      DioExceptionType.sendTimeout =>
        true,
      _ => false,
    };
  }

  @override
  Future<Map<String, dynamic>> submitPuzzleAttempt(
    String puzzleId,
    String moveUci, {
    int? durationSeconds,
  }) async {
    final payload = <String, dynamic>{
      'move_uci': moveUci.trim().toLowerCase(),
      if (durationSeconds != null) 'duration_seconds': durationSeconds,
    };
    try {
      final result = await postJson('/puzzles/$puzzleId/attempt', data: payload);
      return Map<String, dynamic>.from(result as Map);
    } on DioException catch (error) {
      if (!_isConnectivityFailure(error)) rethrow;
      final pending = _readPendingAttempts();
      pending.add({
        'local_id': DateTime.now().microsecondsSinceEpoch.toString(),
        'puzzle_id': puzzleId,
        ...payload,
      });
      await preferences.setString(_pendingAttemptsKey, jsonEncode(pending));
      return {'queued_offline': true};
    }
  }

  List<Map<String, dynamic>> _readPendingAttempts() {
    final raw = preferences.getString(_pendingAttemptsKey);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw) as List<dynamic>;
    return decoded.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  @override
  Future<int> syncPendingPuzzleAttempts() async {
    final pending = _readPendingAttempts();
    if (pending.isEmpty || !isSignedIn) return 0;

    final remaining = <Map<String, dynamic>>[];
    var synced = 0;
    for (final item in pending) {
      final puzzleId = item['puzzle_id'] as String;
      final payload = Map<String, dynamic>.from(item)
        ..remove('local_id')
        ..remove('puzzle_id');
      try {
        await postJson('/puzzles/$puzzleId/attempt', data: payload);
        synced += 1;
      } on DioException catch (error) {
        if (_isConnectivityFailure(error)) {
          remaining.add(item);
          remaining.addAll(pending.skip(synced + remaining.length));
          break;
        }
        // Server-rejected attempts are dropped rather than retried forever.
      }
    }
    await preferences.setString(_pendingAttemptsKey, jsonEncode(remaining));
    return synced;
  }
}
