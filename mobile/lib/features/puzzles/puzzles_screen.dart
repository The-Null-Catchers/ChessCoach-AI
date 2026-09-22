import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';

class PuzzlesScreen extends ConsumerStatefulWidget {
  const PuzzlesScreen({super.key});

  @override
  ConsumerState<PuzzlesScreen> createState() => _PuzzlesScreenState();
}

class _PuzzlesScreenState extends ConsumerState<PuzzlesScreen> {
  final _move = TextEditingController();
  late Future<List<Map<String, dynamic>>> _future;
  int _selected = 0;
  String? _message;
  String? _pendingAttemptId;
  String? _pendingPuzzleId;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _move.dispose();
    super.dispose();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final data = await ref
        .read(apiClientProvider)
        .cachedGet('/puzzles/queue?limit=20', cacheKey: 'mobile_cache_puzzles');
    return (data as List<dynamic>)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = _load();
      _selected = 0;
      _message = null;
    });
    await _future;
  }

  Future<void> _submit(Map<String, dynamic> puzzle) async {
    final move = _move.text.trim();
    if (move.length < 4) return;
    try {
      final result = await ref.read(apiClientProvider).submitPuzzleAttempt(
            puzzle['id'] as String,
            move,
          );
      if (!mounted) return;
      setState(() {
        if (result['queued_offline'] == true) {
          _message =
              'Saved offline. This attempt will sync when the API is reachable.';
          _pendingAttemptId = null;
          _pendingPuzzleId = null;
        } else if (result['correct'] == true) {
          _message = 'Correct. ${result['solution_line'] ?? ''}';
          if (result['requires_grade'] == true) {
            _pendingAttemptId = result['attempt_id'] as String?;
            _pendingPuzzleId = puzzle['id'] as String;
          }
        } else {
          _message =
              'Not quite. Expected ${result['expected_move'] ?? 'the best move'}.';
          _pendingAttemptId = null;
          _pendingPuzzleId = null;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _message = 'The server rejected this move.');
    }
  }

  Future<void> _grade(String grade) async {
    final attemptId = _pendingAttemptId;
    final puzzleId = _pendingPuzzleId;
    if (attemptId == null || puzzleId == null) return;
    await ref.read(apiClientProvider).postJson(
      '/puzzles/$puzzleId/grade',
      data: {'attempt_id': attemptId, 'grade': grade},
    );
    if (!mounted) return;
    setState(() {
      _message = 'Review graded $grade.';
      _pendingAttemptId = null;
      _pendingPuzzleId = null;
      _move.clear();
    });
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<Map<String, dynamic>>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const ListView(
              children: [
                SizedBox(height: 260),
                Center(child: CircularProgressIndicator()),
              ],
            );
          }
          if (snapshot.hasError) {
            return const ListView(
              padding: EdgeInsets.all(24),
              children: [
                SizedBox(height: 120),
                Text(
                  'Unable to load your puzzle queue. Pull to retry.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          final puzzles = snapshot.data ?? const [];
          if (puzzles.isEmpty) {
            return const ListView(
              padding: EdgeInsets.all(24),
              children: [
                SizedBox(height: 120),
                Icon(Icons.extension_outlined, size: 48),
                SizedBox(height: 12),
                Text(
                  'No due puzzles yet. Analyze games to generate training positions from your own mistakes.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          if (_selected >= puzzles.length) _selected = 0;
          final puzzle = puzzles[_selected];

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Puzzle ${_selected + 1} of ${puzzles.length}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Text('${puzzle['difficulty'] ?? '—'}'),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                (puzzle['theme'] as String? ?? 'mixed').replaceAll('_', ' '),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(
                    puzzle['fen'] as String? ?? '',
                    style: const TextStyle(fontFamily: 'monospace'),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _move,
                autocorrect: false,
                textCapitalization: TextCapitalization.none,
                decoration: const InputDecoration(
                  labelText: 'Your move (UCI)',
                  hintText: 'e2e4',
                  helperText:
                      'Board interaction is the next mobile milestone; this uses the real puzzle API now.',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => _submit(puzzle),
                child: const Text('Check move'),
              ),
              if (_message != null) ...[
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Text(_message!),
                  ),
                ),
              ],
              if (_pendingAttemptId != null) ...[
                const SizedBox(height: 8),
                const Text('How difficult was this review?'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    for (final grade in ['Hard', 'Good', 'Easy'])
                      OutlinedButton(
                        onPressed: () => _grade(grade),
                        child: Text(grade),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 20),
              Text(
                'Due queue',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              ...List.generate(puzzles.length, (index) {
                final item = puzzles[index];
                return ListTile(
                  selected: index == _selected,
                  leading: Text('${index + 1}'),
                  title: Text(
                    (item['theme'] as String? ?? 'mixed').replaceAll('_', ' '),
                  ),
                  subtitle: Text(
                    'Repetitions ${item['repetitions'] ?? 0} · '
                    'lapses ${item['lapses'] ?? 0}',
                  ),
                  onTap: () {
                    setState(() {
                      _selected = index;
                      _message = null;
                      _pendingAttemptId = null;
                      _pendingPuzzleId = null;
                      _move.clear();
                    });
                  },
                );
              }),
            ],
          );
        },
      ),
    );
  }
}
