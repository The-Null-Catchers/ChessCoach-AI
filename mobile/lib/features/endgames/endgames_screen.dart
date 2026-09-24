import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';

class EndgamesScreen extends ConsumerStatefulWidget {
  const EndgamesScreen({super.key});

  @override
  ConsumerState<EndgamesScreen> createState() => _EndgamesScreenState();
}

class _EndgamesScreenState extends ConsumerState<EndgamesScreen> {
  Map<String, dynamic>? _overview;
  List<Map<String, dynamic>> _queue = const [];
  String? _candidateMove;
  String? _message;
  bool _loading = true;
  bool _submitting = false;
  int _boardRevision = 0;

  Map<String, dynamic>? get _current =>
      _queue.isEmpty ? null : _queue.first;

  @override
  void initState() {
    super.initState();
    Future<void>.microtask(_load);
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final results = await Future.wait([
        api.cachedGet(
          '/endgames/trainer/overview',
          cacheKey: 'endgame_trainer_overview',
        ),
        api.cachedGet(
          '/endgames/trainer/queue?limit=20',
          cacheKey: 'endgame_trainer_queue',
        ),
      ]);
      if (!mounted) return;
      setState(() {
        _overview = Map<String, dynamic>.from(results[0] as Map);
        _queue = (results[1] as List<dynamic>)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList(growable: false);
        _candidateMove = null;
        _boardRevision += 1;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _message = 'Could not load endgame training.';
      });
    }
  }

  Future<void> _submit(String grade) async {
    final current = _current;
    final move = _candidateMove;
    if (current == null || move == null || _submitting) return;
    setState(() => _submitting = true);
    try {
      final response = Map<String, dynamic>.from(
        await ref.read(apiClientProvider).postJson(
              '/endgames/trainer/${current['exercise_id']}/attempt',
              data: {'move_uci': move, 'grade': grade},
            ) as Map,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(
            response['correct'] == true ? 'Correct' : 'Review this technique',
          ),
          content: Text(
            '${response['explanation']}\n\n'
            'Target move: ${response['expected_move_uci']}\n'
            'Mastery: ${response['mastery']}%',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Next'),
            ),
          ],
        ),
      );
      if (mounted) await _load();
    } catch (_) {
      if (mounted) {
        setState(() {
          _candidateMove = null;
          _boardRevision += 1;
          _message = 'Could not submit this endgame attempt.';
        });
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _overview == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final current = _current;
    final categories = (_overview?['categories'] as List<dynamic>? ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList(growable: false);

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Endgame trainer',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 6),
          const Text('Practice endgame technique with spaced repetition.'),
          if (_message != null) ...[
            const SizedBox(height: 10),
            Text(_message!),
          ],
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(label: Text('${_overview?['due'] ?? 0} due')),
              Chip(label: Text('${_overview?['mastery'] ?? 0}% mastery')),
              for (final category in categories.take(3))
                Chip(
                  label: Text(
                    '${category['category'].toString().replaceAll('_', ' ')} '
                    '${category['mastery']}%',
                  ),
                ),
            ],
          ),
          const SizedBox(height: 18),
          if (current == null)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No endgame positions are due right now.'),
              ),
            )
          else ...[
            Text(
              current['title'] as String,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(current['objective'] as String),
            const SizedBox(height: 10),
            Text(
              '${current['category'].toString().replaceAll('_', ' ')} · '
              'difficulty ${current['difficulty']} · '
              '${current['mastery']}% mastery',
            ),
            const SizedBox(height: 14),
            AspectRatio(
              aspectRatio: 1,
              child: ChessPositionBoard(
                key: ValueKey(
                  '${current['exercise_id']}-$_boardRevision',
                ),
                fen: current['fen'] as String,
                enabled: _candidateMove == null && !_submitting,
                onMove: (uci) async {
                  if (mounted) setState(() => _candidateMove = uci);
                },
              ),
            ),
            const SizedBox(height: 12),
            if (_candidateMove == null)
              const Text('Tap or drag a piece to choose your move.')
            else ...[
              Text('Selected move: $_candidateMove'),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: _submitting ? null : () => _submit('again'),
                    child: const Text('Again'),
                  ),
                  OutlinedButton(
                    onPressed: _submitting ? null : () => _submit('hard'),
                    child: const Text('Hard'),
                  ),
                  FilledButton.tonal(
                    onPressed: _submitting ? null : () => _submit('good'),
                    child: const Text('Good'),
                  ),
                  FilledButton(
                    onPressed: _submitting ? null : () => _submit('easy'),
                    child: const Text('Easy'),
                  ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }
}
