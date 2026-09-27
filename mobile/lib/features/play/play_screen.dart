import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';

class PlayScreen extends ConsumerStatefulWidget {
  const PlayScreen({super.key});

  @override
  ConsumerState<PlayScreen> createState() => _PlayScreenState();
}

class _PlayScreenState extends ConsumerState<PlayScreen> {
  static const _clocks = <({String label, int? seconds, int increment, String value})>[
    (label: 'No clock', seconds: null, increment: 0, value: '-'),
    (label: '3 + 2', seconds: 180, increment: 2, value: '180+2'),
    (label: '5 + 0', seconds: 300, increment: 0, value: '300+0'),
    (label: '10 + 0', seconds: 600, increment: 0, value: '600+0'),
  ];

  final _fenController = TextEditingController();
  String _opponent = 'engine';
  String _playerColor = 'white';
  double _level = 8;
  double _elo = 1600;
  final List<Map<String, dynamic>> _history = [];
  int _clockIndex = 2;
  Map<String, dynamic>? _state;
  final List<String> _moves = [];
  bool _busy = false;
  String? _message;
  String? _savedGameId;
  int? _whiteSeconds = 300;
  int? _blackSeconds = 300;
  String? _timedOut;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _fenController.dispose();
    super.dispose();
  }

  void _startClock() {
    _timer?.cancel();
    if (_clocks[_clockIndex].seconds == null) return;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted || _busy || _state == null || _state!['game_over'] == true || _timedOut != null) return;
      final turn = _state!['turn'] as String?;
      setState(() {
        if (turn == 'white' && _whiteSeconds != null) {
          _whiteSeconds = (_whiteSeconds! - 1).clamp(0, 86400).toInt();
          if (_whiteSeconds == 0) _timedOut = 'white';
        } else if (turn == 'black' && _blackSeconds != null) {
          _blackSeconds = (_blackSeconds! - 1).clamp(0, 86400).toInt();
          if (_blackSeconds == 0) _timedOut = 'black';
        }
      });
    });
  }

  String _clockText(int? seconds) {
    if (seconds == null) return '∞';
    final minutes = seconds ~/ 60;
    final rest = seconds % 60;
    return '$minutes:${rest.toString().padLeft(2, '0')}';
  }

  Future<void> _start() async {
    setState(() {
      _busy = true;
      _message = null;
      _savedGameId = null;
      _timedOut = null;
    });
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/start',
        data: {
          'opponent': _opponent,
          'player_color': _playerColor,
          'level': _level.round(),
          'elo': _elo.round(),
          'elo': _elo.round(),
          'initial_fen': _fenController.text.trim().isEmpty ? null : _fenController.text.trim(),
        },
      );
      final next = Map<String, dynamic>.from(result as Map);
      final seconds = _clocks[_clockIndex].seconds;
      setState(() {
        _state = next;
        _history.clear();
        _moves
          ..clear()
          ..addAll(next['engine_move'] == null ? const [] : [next['engine_move'] as String]);
        _whiteSeconds = seconds;
        _blackSeconds = seconds;
        _busy = false;
      });
      _startClock();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _message = 'Could not start the game. Check the FEN and connection.';
      });
    }
  }

  Future<void> _saveCompleted(List<String> moves, {String? resultOverride, String? termination}) async {
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/complete',
        data: {
          'moves': moves,
          'initial_fen': _fenController.text.trim().isEmpty ? null : _fenController.text.trim(),
          'player_color': _playerColor,
          'opponent': _opponent,
          'level': _level.round(),
          'elo': _elo.round(),
          'result_override': resultOverride,
          'termination': termination,
          'time_control': _clocks[_clockIndex].value,
        },
      );
      if (!mounted) return;
      setState(() {
        _savedGameId = (result as Map)['game_id'] as String?;
        _message = 'Game saved and queued for coaching analysis. Open Games to review it.';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _message = 'Game finished, but saving it for analysis failed.');
    }
  }

  Future<void> _move(String uci) async {
    final current = _state;
    if (current == null || _busy || _timedOut != null) return;
    final mover = current['turn'] as String;
    setState(() => _busy = true);
    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/move',
        data: {
          'fen': current['fen'],
          'move_uci': uci,
          'opponent': _opponent,
          'player_color': _playerColor,
          'level': _level.round(),
        },
      );
      final next = Map<String, dynamic>.from(result as Map);
      _history.add(Map<String, dynamic>.from(current));
      final added = <String>[uci];
      if (next['engine_move'] != null) added.add(next['engine_move'] as String);
      final nextMoves = <String>[..._moves, ...added];
      final increment = _clocks[_clockIndex].increment;
      setState(() {
        _state = next;
        _moves
          ..clear()
          ..addAll(nextMoves);
        _busy = false;
        if (increment > 0) {
          if (mover == 'white' && _whiteSeconds != null) _whiteSeconds = _whiteSeconds! + increment;
          if (mover == 'black' && _blackSeconds != null) _blackSeconds = _blackSeconds! + increment;
          if (next['engine_move'] != null) {
            if (mover == 'white' && _blackSeconds != null) _blackSeconds = _blackSeconds! + increment;
            if (mover == 'black' && _whiteSeconds != null) _whiteSeconds = _whiteSeconds! + increment;
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
        _busy = false;
        _message = 'That move could not be played.';
      });
    }
  }

  bool get _canMove {
    if (_state == null || _busy || _timedOut != null || _state!['game_over'] == true) return false;
    if (_opponent == 'local') return true;
    return _state!['turn'] == _playerColor;
  }

  @override
  Widget build(BuildContext context) {
    final state = _state;
    final gameOver = state?['game_over'] == true;
    final status = _timedOut != null
        ? '${_timedOut == 'white' ? 'White' : 'Black'} ran out of time'
        : gameOver
            ? 'Game over · ${state?['result'] ?? '*'}'
            : state == null
                ? 'Configure a game to begin'
                : '${state['check'] == true ? 'Check · ' : ''}${state['turn']} to move';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Play & Learn', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        const Text('Play a legal game, then turn it directly into a coaching review.'),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            DropdownMenu<String>(
              label: const Text('Opponent'),
              initialSelection: _opponent,
              dropdownMenuEntries: const [
                DropdownMenuEntry(value: 'engine', label: 'ChessCoach Engine'),
                DropdownMenuEntry(value: 'local', label: 'Local two-player'),
              ],
              onSelected: (value) => setState(() => _opponent = value ?? 'engine'),
            ),
            DropdownMenu<String>(
              label: const Text('Your color'),
              enabled: _opponent == 'engine',
              initialSelection: _playerColor,
              dropdownMenuEntries: const [
                DropdownMenuEntry(value: 'white', label: 'White'),
                DropdownMenuEntry(value: 'black', label: 'Black'),
              ],
              onSelected: (value) => setState(() => _playerColor = value ?? 'white'),
            ),
            DropdownMenu<int>(
              label: const Text('Clock'),
              initialSelection: _clockIndex,
              dropdownMenuEntries: [
                for (var i = 0; i < _clocks.length; i++)
                  DropdownMenuEntry(value: i, label: _clocks[i].label),
              ],
              onSelected: (value) => setState(() => _clockIndex = value ?? 2),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            const Text('Engine ELO'),
            Expanded(
              child: Slider(
                value: _elo,
                min: 800,
                max: 2800,
                divisions: 20,
                label: _elo.round().toString(),
                onChanged: _opponent == 'engine' ? (value) => setState(() => _elo = value) : null,
              ),
            ),
            Text('${_elo.round()}'),
          ],
        ),
        TextField(
          controller: _fenController,
          decoration: const InputDecoration(
            labelText: 'Custom FEN (optional)',
            hintText: 'Leave empty for the normal starting position',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _busy ? null : _start,
          icon: const Icon(Icons.play_arrow),
          label: Text(state == null ? 'Start game' : 'New game'),
        ),
        if (_message != null) ...[
          const SizedBox(height: 10),
          Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(_message!))),
        ],
        if (state != null) ...[
          const SizedBox(height: 18),
          _ClockTile(label: 'Black', value: _clockText(_blackSeconds), active: state['turn'] == 'black'),
          AspectRatio(
            aspectRatio: 1,
            child: ChessPositionBoard(
              fen: state['fen'] as String,
              enabled: _canMove,
              whiteAtBottom: _opponent == 'local' || _playerColor == 'white',
              lastMoveUci: _moves.isEmpty ? null : _moves.last,
              onMove: _move,
            ),
          ),
          _ClockTile(label: 'White', value: _clockText(_whiteSeconds), active: state['turn'] == 'white'),
          const SizedBox(height: 12),
          Text(status, style: Theme.of(context).textTheme.titleMedium),
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
                if (_opponent == 'local' && _history.isNotEmpty)
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
                if (_opponent == 'local' && _moves.isNotEmpty)
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
                  onPressed: () {
                    final loser = state['turn'] as String;
                    final result = loser == 'white' ? '0-1' : '1-0';
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
            const SizedBox(height: 8),
            FilledButton.tonalIcon(
              onPressed: _busy ? null : _start,
              icon: const Icon(Icons.replay),
              label: const Text('Rematch'),
            ),
          ],
          if (_savedGameId != null) ...[
            const SizedBox(height: 8),
            const Text('The analysis job has been queued automatically.'),
          ],
        ],
      ],
    );
  }
}

class _ClockTile extends StatelessWidget {
  const _ClockTile({required this.label, required this.value, required this.active});

  final String label;
  final String value;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: active ? Theme.of(context).colorScheme.primaryContainer : null,
      child: ListTile(
        dense: true,
        title: Text(label),
        trailing: Text(value, style: Theme.of(context).textTheme.titleLarge),
      ),
    );
  }
}
