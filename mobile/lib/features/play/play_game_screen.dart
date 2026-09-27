import 'dart:async';

import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';
import 'play_screen.dart';

class PlayGameScreen extends ConsumerStatefulWidget {
  const PlayGameScreen({
    required this.config,
    required this.initialState,
    super.key,
  });

  final PlayGameConfig config;
  final Map<String, dynamic> initialState;

  @override
  ConsumerState<PlayGameScreen> createState() => _PlayGameScreenState();
}

class _PlayGameScreenState extends ConsumerState<PlayGameScreen> {
  late Map<String, dynamic> _state;
  final List<Map<String, dynamic>> _history = [];
  final List<String> _moves = [];
  Timer? _timer;
  bool _requestInFlight = false;
  bool _opponentThinking = false;
  bool _showHint = false;
  bool _startingRematch = false;
  String? _message;
  String? _savedGameId;
  String? _timedOut;
  int? _whiteSeconds;
  int? _blackSeconds;

  @override
  void initState() {
    super.initState();
    _resetFrom(widget.initialState);
    _startClock();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _resetFrom(Map<String, dynamic> next) {
    _state = Map<String, dynamic>.from(next);
    _history.clear();
    _moves
      ..clear()
      ..addAll(
        next['engine_move'] == null
            ? const <String>[]
            : <String>[next['engine_move'] as String],
      );
    _whiteSeconds = widget.config.clockSeconds;
    _blackSeconds = widget.config.clockSeconds;
    _timedOut = null;
    _savedGameId = null;
    _message = null;
    _requestInFlight = false;
    _opponentThinking = false;
    _showHint = false;
  }

  void _startClock() {
    _timer?.cancel();
    if (widget.config.clockSeconds == null) return;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted || _state['game_over'] == true || _timedOut != null) return;
      final turn = _state['turn'] as String?;
      setState(() {
        if (turn == 'white' && _whiteSeconds != null) {
          _whiteSeconds = (_whiteSeconds! - 1).clamp(0, 86400).toInt();
          if (_whiteSeconds == 0) _timedOut = 'white';
        } else if (turn == 'black' && _blackSeconds != null) {
          _blackSeconds = (_blackSeconds! - 1).clamp(0, 86400).toInt();
          if (_blackSeconds == 0) _timedOut = 'black';
        }
      });
      if (_timedOut != null) {
        _timer?.cancel();
        if (_moves.isNotEmpty) {
          final result = _timedOut == 'white' ? '0-1' : '1-0';
          _saveCompleted(
            List<String>.from(_moves),
            resultOverride: result,
            termination: 'time forfeit',
          );
        }
      }
    });
  }

  String _clockText(int? seconds) {
    if (seconds == null) return '∞';
    final minutes = seconds ~/ 60;
    final rest = seconds % 60;
    return '$minutes:${rest.toString().padLeft(2, '0')}';
  }

  String _localFenAfterMove(String fen, String uci) {
    final game = chess.Chess.fromFEN(fen);
    final move = <String, String>{
      'from': uci.substring(0, 2),
      'to': uci.substring(2, 4),
      if (uci.length > 4) 'promotion': uci.substring(4, 5),
    };
    if (!game.move(move)) {
      throw const FormatException('Illegal local move');
    }
    return game.fen;
  }

  String _turnFromFen(String fen) {
    final parts = fen.trim().split(RegExp(r'\s+'));
    return parts.length > 1 && parts[1] == 'b' ? 'black' : 'white';
  }

  Future<void> _saveCompleted(
    List<String> moves, {
    String? resultOverride,
    String? termination,
  }) async {
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/complete',
        data: {
          'moves': moves,
          'initial_fen': widget.config.initialFen,
          'player_color': widget.config.playerColor,
          'opponent': widget.config.opponent,
          'level': widget.config.level,
          'elo': widget.config.elo,
          'difficulty': widget.config.difficulty,
          'style': widget.config.style,
          'result_override': resultOverride,
          'termination': termination,
          'time_control': widget.config.timeControl,
        },
      );
      if (!mounted) return;
      setState(() {
        _savedGameId = (result as Map)['game_id'] as String?;
        _message =
            'Game saved and queued for coaching analysis. Open Games to review it.';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _message = 'Game finished, but saving it for analysis failed.';
      });
    }
  }

  Future<void> _move(String uci) async {
    if (_requestInFlight || _timedOut != null || _state['game_over'] == true) {
      return;
    }

    final current = Map<String, dynamic>.from(_state);
    final mover = current['turn'] as String;
    final currentFen = current['fen'] as String;
    String localFen;
    try {
      localFen = _localFenAfterMove(currentFen, uci);
    } catch (_) {
      return;
    }

    final localState = Map<String, dynamic>.from(current)
      ..['fen'] = localFen
      ..['turn'] = _turnFromFen(localFen)
      ..['check'] = false
      ..remove('coach_feedback')
      ..remove('challenge');

    final movesBefore = List<String>.from(_moves);
    final localMoves = <String>[...movesBefore, uci];
    final increment = widget.config.increment;

    setState(() {
      _history.add(current);
      _state = localState;
      _moves
        ..clear()
        ..addAll(localMoves);
      _requestInFlight = true;
      _opponentThinking = widget.config.opponent == 'engine';
      _showHint = false;
      _message = null;
      if (increment > 0) {
        if (mover == 'white' && _whiteSeconds != null) {
          _whiteSeconds = _whiteSeconds! + increment;
        }
        if (mover == 'black' && _blackSeconds != null) {
          _blackSeconds = _blackSeconds! + increment;
        }
      }
    });

    final started = DateTime.now();
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/move',
        data: {
          'fen': currentFen,
          'move_uci': uci,
          'opponent': widget.config.opponent,
          'player_color': widget.config.playerColor,
          'level': widget.config.level,
          'elo': widget.config.elo,
          'difficulty': widget.config.difficulty,
          'style': widget.config.style,
          'coach_mode': widget.config.coachMode,
        },
      );

      final next = Map<String, dynamic>.from(result as Map);
      final engineMove = next['engine_move'] as String?;
      if (engineMove != null) {
        final elapsed = DateTime.now().difference(started);
        const minimumThinkingTime = Duration(milliseconds: 420);
        if (elapsed < minimumThinkingTime) {
          await Future<void>.delayed(minimumThinkingTime - elapsed);
        }
      }
      if (!mounted) return;

      final nextMoves = <String>[
        ...localMoves,
        if (engineMove != null) engineMove,
      ];

      setState(() {
        _state = next;
        _moves
          ..clear()
          ..addAll(nextMoves);
        _requestInFlight = false;
        _opponentThinking = false;
        if (engineMove != null && increment > 0) {
          if (mover == 'white' && _blackSeconds != null) {
            _blackSeconds = _blackSeconds! + increment;
          }
          if (mover == 'black' && _whiteSeconds != null) {
            _whiteSeconds = _whiteSeconds! + increment;
          }
        }
      });

      if (next['game_over'] == true) {
        _timer?.cancel();
        await _saveCompleted(nextMoves);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        if (_history.isNotEmpty) {
          _state = _history.removeLast();
        } else {
          _state = current;
        }
        _moves
          ..clear()
          ..addAll(movesBefore);
        _requestInFlight = false;
        _opponentThinking = false;
        _message = 'That move could not be played.';
      });
    }
  }

  bool get _canMove {
    if (_requestInFlight ||
        _timedOut != null ||
        _state['game_over'] == true) {
      return false;
    }
    if (widget.config.opponent == 'local') return true;
    return _state['turn'] == widget.config.playerColor;
  }

  Future<void> _rematch() async {
    if (_startingRematch) return;
    setState(() {
      _startingRematch = true;
      _message = null;
    });
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/start',
        data: {
          'opponent': widget.config.opponent,
          'player_color': widget.config.playerColor,
          'level': widget.config.level,
          'elo': widget.config.elo,
          'difficulty': widget.config.difficulty,
          'style': widget.config.style,
          'initial_fen': widget.config.initialFen,
        },
      );
      if (!mounted) return;
      setState(() {
        _resetFrom(Map<String, dynamic>.from(result as Map));
        _startingRematch = false;
      });
      _startClock();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _startingRematch = false;
        _message = 'Could not start the rematch.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final gameOver = _state['game_over'] == true;
    final status = _opponentThinking
        ? 'ChessCoach is thinking…'
        : _timedOut == 'draw'
            ? 'Draw agreed'
            : _timedOut != null
                ? '${_timedOut == 'white' ? 'White' : 'Black'} ran out of time'
                : gameOver
                    ? 'Game over · ${_state['result'] ?? '*'}'
                    : '${_state['check'] == true ? 'Check · ' : ''}${_state['turn']} to move';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Game'),
        actions: [
          IconButton(
            tooltip: 'Game setup',
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.tune),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            _ClockTile(
              label: 'Black',
              value: _clockText(_blackSeconds),
              active: _state['turn'] == 'black',
              thinking: _opponentThinking && _state['turn'] == 'black',
            ),
            const SizedBox(height: 4),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              switchInCurve: Curves.easeOut,
              switchOutCurve: Curves.easeIn,
              child: AspectRatio(
                key: ValueKey<String>(_state['fen'] as String),
                aspectRatio: 1,
                child: ChessPositionBoard(
                  fen: _state['fen'] as String,
                  enabled: _canMove,
                  whiteAtBottom: widget.config.opponent == 'local' ||
                      widget.config.playerColor == 'white',
                  lastMoveUci: _moves.isEmpty ? null : _moves.last,
                  onMove: _move,
                ),
              ),
            ),
            const SizedBox(height: 4),
            _ClockTile(
              label: 'White',
              value: _clockText(_whiteSeconds),
              active: _state['turn'] == 'white',
              thinking: _opponentThinking && _state['turn'] == 'white',
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 160),
                    child: Text(
                      status,
                      key: ValueKey<String>(status),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                ),
                if (_opponentThinking)
                  const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
            if (_opponentThinking) ...[
              const SizedBox(height: 8),
              const LinearProgressIndicator(minHeight: 2),
            ],
            if (_message != null) ...[
              const SizedBox(height: 10),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(_message!),
                ),
              ),
            ],
            if (widget.config.coachMode && _state['coach_feedback'] is Map) ...[
              const SizedBox(height: 10),
              _CoachFeedbackCard(
                feedback: Map<String, dynamic>.from(
                  _state['coach_feedback'] as Map,
                ),
              ),
            ],
            if (_state['challenge'] is Map) ...[
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Builder(
                    builder: (context) {
                      final challenge = Map<String, dynamic>.from(
                        _state['challenge'] as Map,
                      );
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'LIVE CHALLENGE',
                            style: Theme.of(context).textTheme.labelSmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${challenge['title']}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 6),
                          if (_showHint)
                            Text('${challenge['hint']}')
                          else
                            OutlinedButton.icon(
                              onPressed: () =>
                                  setState(() => _showHint = true),
                              icon: const Icon(Icons.lightbulb_outline),
                              label: const Text('Show hint'),
                            ),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (var i = 0; i < _moves.length; i++)
                  Chip(label: Text('${i + 1}. ${_moves[i]}')),
              ],
            ),
            if (!gameOver && _timedOut == null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (widget.config.opponent == 'local' &&
                      _history.isNotEmpty &&
                      !_requestInFlight)
                    OutlinedButton.icon(
                      onPressed: () {
                        final previous = _history.removeLast();
                        setState(() {
                          _state = previous;
                          if (_moves.isNotEmpty) _moves.removeLast();
                        });
                      },
                      icon: const Icon(Icons.undo),
                      label: const Text('Undo'),
                    ),
                  if (widget.config.opponent == 'local' &&
                      _moves.isNotEmpty &&
                      !_requestInFlight)
                    OutlinedButton.icon(
                      onPressed: () {
                        _timer?.cancel();
                        setState(() => _timedOut = 'draw');
                        _saveCompleted(
                          List<String>.from(_moves),
                          resultOverride: '1/2-1/2',
                          termination: 'agreed draw',
                        );
                      },
                      icon: const Icon(Icons.handshake_outlined),
                      label: const Text('Agree draw'),
                    ),
                  OutlinedButton.icon(
                    onPressed: _requestInFlight
                        ? null
                        : () {
                            final loser = _state['turn'] as String;
                            final result =
                                loser == 'white' ? '0-1' : '1-0';
                            _timer?.cancel();
                            setState(() => _timedOut = loser);
                            if (_moves.isNotEmpty) {
                              _saveCompleted(
                                List<String>.from(_moves),
                                resultOverride: result,
                                termination: 'resignation',
                              );
                            }
                          },
                    icon: const Icon(Icons.flag_outlined),
                    label: const Text('Resign'),
                  ),
                ],
              ),
            ],
            if (gameOver || _timedOut != null) ...[
              const SizedBox(height: 12),
              FilledButton.tonalIcon(
                onPressed: _startingRematch ? null : _rematch,
                icon: _startingRematch
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.replay),
                label: const Text('Rematch'),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.tune),
                label: const Text('Change game settings'),
              ),
            ],
            if (_savedGameId != null) ...[
              const SizedBox(height: 8),
              const Text(
                'The analysis job has been queued automatically.',
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ClockTile extends StatelessWidget {
  const _ClockTile({
    required this.label,
    required this.value,
    required this.active,
    required this.thinking,
  });

  final String label;
  final String value;
  final bool active;
  final bool thinking;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: active ? scheme.primaryContainer : null,
      child: ListTile(
        dense: true,
        title: Row(
          children: [
            Text(label),
            if (thinking) ...[
              const SizedBox(width: 8),
              Text(
                'thinking…',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: scheme.primary,
                    ),
              ),
            ],
          ],
        ),
        trailing: Text(
          value,
          style: Theme.of(context).textTheme.titleLarge,
        ),
      ),
    );
  }
}

class _CoachFeedbackCard extends StatelessWidget {
  const _CoachFeedbackCard({required this.feedback});

  final Map<String, dynamic> feedback;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'COACH FEEDBACK',
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(height: 4),
            Text(
              '${feedback['title']}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text('${feedback['message']}'),
          ],
        ),
      ),
    );
  }
}
