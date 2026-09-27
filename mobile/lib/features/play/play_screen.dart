import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import 'play_game_screen.dart';

class PlayGameConfig {
  const PlayGameConfig({
    required this.opponent,
    required this.playerColor,
    required this.level,
    required this.elo,
    required this.difficulty,
    required this.style,
    required this.coachMode,
    required this.initialFen,
    required this.clockSeconds,
    required this.increment,
    required this.timeControl,
  });

  final String opponent;
  final String playerColor;
  final int level;
  final int elo;
  final String difficulty;
  final String style;
  final bool coachMode;
  final String? initialFen;
  final int? clockSeconds;
  final int increment;
  final String timeControl;
}

class PlayScreen extends ConsumerStatefulWidget {
  const PlayScreen({super.key});

  @override
  ConsumerState<PlayScreen> createState() => _PlayScreenState();
}

class _PlayScreenState extends ConsumerState<PlayScreen> {
  static const _clocks =
      <({String label, int? seconds, int increment, String value})>[
    (label: 'No clock', seconds: null, increment: 0, value: '-'),
    (label: '3 + 2', seconds: 180, increment: 2, value: '180+2'),
    (label: '5 + 0', seconds: 300, increment: 0, value: '300+0'),
    (label: '10 + 0', seconds: 600, increment: 0, value: '600+0'),
  ];

  final _fenController = TextEditingController();
  String _opponent = 'engine';
  String _playerColor = 'white';
  final double _level = 8;
  double _elo = 1400;
  String _difficulty = 'intermediate';
  String _style = 'balanced';
  bool _coachMode = true;
  int _clockIndex = 2;
  bool _busy = false;
  String? _message;

  @override
  void dispose() {
    _fenController.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final initialFen =
        _fenController.text.trim().isEmpty ? null : _fenController.text.trim();
    final clock = _clocks[_clockIndex];
    final config = PlayGameConfig(
      opponent: _opponent,
      playerColor: _playerColor,
      level: _level.round(),
      elo: _elo.round(),
      difficulty: _difficulty,
      style: _style,
      coachMode: _coachMode,
      initialFen: initialFen,
      clockSeconds: clock.seconds,
      increment: clock.increment,
      timeControl: clock.value,
    );

    setState(() {
      _busy = true;
      _message = null;
    });

    try {
      final result = await ref.read(apiClientProvider).postJson(
        '/play/start',
        data: {
          'opponent': config.opponent,
          'player_color': config.playerColor,
          'level': config.level,
          'elo': config.elo,
          'difficulty': config.difficulty,
          'style': config.style,
          'initial_fen': config.initialFen,
        },
      );
      if (!mounted) return;
      final initialState = Map<String, dynamic>.from(result as Map);
      setState(() => _busy = false);

      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => PlayGameScreen(
            config: config,
            initialState: initialState,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      var message = 'Could not start the game.';
      if (error is DioException) {
        final detail =
            error.response?.data is Map ? (error.response?.data as Map)['detail'] : null;
        if (detail is String && detail.isNotEmpty) {
          message = 'Could not start the game: $detail';
        } else if (error.response?.statusCode != null) {
          message =
              'Could not start the game (HTTP ${error.response!.statusCode}).';
        } else {
          message =
              'Could not reach ChessCoach API. Check the server connection.';
        }
      }
      setState(() {
        _busy = false;
        _message = message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Play & Learn', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        const Text(
          'Choose your opponent and training settings. The game opens in a dedicated board view.',
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            DropdownMenu<String>(
              label: const Text('Opponent'),
              initialSelection: _opponent,
              dropdownMenuEntries: const [
                DropdownMenuEntry(
                  value: 'engine',
                  label: 'ChessCoach Engine',
                ),
                DropdownMenuEntry(value: 'local', label: 'Local two-player'),
              ],
              onSelected: (value) =>
                  setState(() => _opponent = value ?? 'engine'),
            ),
            DropdownMenu<String>(
              label: const Text('Your color'),
              enabled: _opponent == 'engine',
              initialSelection: _playerColor,
              dropdownMenuEntries: const [
                DropdownMenuEntry(value: 'white', label: 'White'),
                DropdownMenuEntry(value: 'black', label: 'Black'),
              ],
              onSelected: (value) =>
                  setState(() => _playerColor = value ?? 'white'),
            ),
            DropdownMenu<String>(
              label: const Text('Difficulty'),
              enabled: _opponent == 'engine',
              initialSelection: _difficulty,
              dropdownMenuEntries: const [
                DropdownMenuEntry(
                  value: 'beginner',
                  label: 'Beginner · 900',
                ),
                DropdownMenuEntry(
                  value: 'intermediate',
                  label: 'Intermediate · 1400',
                ),
                DropdownMenuEntry(
                  value: 'advanced',
                  label: 'Advanced · 1900',
                ),
                DropdownMenuEntry(
                  value: 'master',
                  label: 'Master · 2400',
                ),
              ],
              onSelected: (value) {
                final next = value ?? 'intermediate';
                const eloByDifficulty = {
                  'beginner': 900.0,
                  'intermediate': 1400.0,
                  'advanced': 1900.0,
                  'master': 2400.0,
                };
                setState(() {
                  _difficulty = next;
                  _elo = eloByDifficulty[next] ?? 1400.0;
                });
              },
            ),
            DropdownMenu<String>(
              label: const Text('Engine style'),
              enabled: _opponent == 'engine',
              initialSelection: _style,
              dropdownMenuEntries: const [
                DropdownMenuEntry(value: 'balanced', label: 'Balanced'),
                DropdownMenuEntry(value: 'aggressive', label: 'Aggressive'),
                DropdownMenuEntry(value: 'positional', label: 'Positional'),
                DropdownMenuEntry(value: 'defensive', label: 'Defensive'),
              ],
              onSelected: (value) =>
                  setState(() => _style = value ?? 'balanced'),
            ),
            DropdownMenu<String>(
              label: const Text('Coach mode'),
              initialSelection: _coachMode ? 'on' : 'off',
              dropdownMenuEntries: const [
                DropdownMenuEntry(value: 'on', label: 'On · live feedback'),
                DropdownMenuEntry(value: 'off', label: 'Off · no live evaluation'),
              ],
              onSelected: (value) =>
                  setState(() => _coachMode = value != 'off'),
            ),
            DropdownMenu<int>(
              label: const Text('Clock'),
              initialSelection: _clockIndex,
              dropdownMenuEntries: [
                for (var i = 0; i < _clocks.length; i++)
                  DropdownMenuEntry(value: i, label: _clocks[i].label),
              ],
              onSelected: (value) =>
                  setState(() => _clockIndex = value ?? 2),
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
                onChanged: _opponent == 'engine'
                    ? (value) => setState(() => _elo = value)
                    : null,
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
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: _busy ? null : _start,
          icon: _busy
              ? const SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.play_arrow),
          label: const Text('Start game'),
        ),
        if (_message != null) ...[
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_message!),
            ),
          ),
        ],
      ],
    );
  }
}
