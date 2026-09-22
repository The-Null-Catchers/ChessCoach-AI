import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';

class PuzzlesScreen extends ConsumerStatefulWidget {
  const PuzzlesScreen({super.key});

  @override
  ConsumerState<PuzzlesScreen> createState() => _PuzzlesScreenState();
}

class _PuzzlesScreenState extends ConsumerState<PuzzlesScreen> {
  late Future<List<Map<String, dynamic>>> _future;
  int _selected = 0;
  int _boardRevision = 0;
  bool _flipped = false;
  String? _message;
  String? _pendingAttemptId;
  String? _pendingPuzzleId;

  @override
  void initState() {
    super.initState();
    _future = _load();
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
      _boardRevision += 1;
      _flipped = false;
      _message = null;
      _pendingAttemptId = null;
      _pendingPuzzleId = null;
    });
    await _future;
  }

  Future<void> _submitMove(
    Map<String, dynamic> puzzle,
    String move,
  ) async {
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
          _boardRevision += 1;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _message = 'The server rejected this move.';
        _boardRevision += 1;
      });
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
      _boardRevision += 1;
    });
    await _refresh();
  }

  bool _whiteToMove(String fen) {
    final parts = fen.trim().split(RegExp(r'\s+'));
    return parts.length > 1 && parts[1] == 'w';
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<Map<String, dynamic>>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return ListView(
              children: const [
                SizedBox(height: 260),
                Center(child: CircularProgressIndicator()),
              ],
            );
          }
          if (snapshot.hasError) {
            return ListView(
              padding: const EdgeInsets.all(24),
              children: const [
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
            return ListView(
              padding: const EdgeInsets.all(24),
              children: const [
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
          final fen = puzzle['fen'] as String;
          final defaultWhiteAtBottom = _whiteToMove(fen);
          final whiteAtBottom =
              _flipped ? !defaultWhiteAtBottom : defaultWhiteAtBottom;

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
                  IconButton(
                    tooltip: 'Flip board',
                    onPressed: () => setState(() => _flipped = !_flipped),
                    icon: const Icon(Icons.swap_vert),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                (puzzle['theme'] as String? ?? 'mixed').replaceAll('_', ' '),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
              ),
              const SizedBox(height: 12),
              AspectRatio(
                aspectRatio: 1,
                child: ChessPositionBoard(
                  key: ValueKey(
                    '${puzzle['id']}:$_boardRevision',
                  ),
                  fen: fen,
                  enabled: _pendingAttemptId == null,
                  whiteAtBottom: whiteAtBottom,
                  onMove: (uci) => _submitMove(puzzle, uci),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                _pendingAttemptId == null
                    ? 'Find the strongest move. Tap a piece, then a highlighted legal square, or drag the piece.'
                    : 'Correct. Grade the review before continuing.',
                style: Theme.of(context).textTheme.bodyMedium,
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
                      _boardRevision += 1;
                      _flipped = false;
                      _message = null;
                      _pendingAttemptId = null;
                      _pendingPuzzleId = null;
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
