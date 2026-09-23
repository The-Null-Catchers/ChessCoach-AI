import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';

class GamesScreen extends ConsumerStatefulWidget {
  const GamesScreen({super.key});

  @override
  ConsumerState<GamesScreen> createState() => _GamesScreenState();
}

class _GamesScreenState extends ConsumerState<GamesScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final data = await ref
        .read(apiClientProvider)
        .cachedGet('/games?limit=50', cacheKey: 'mobile_cache_games');
    return (data as List<dynamic>)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
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
                Icon(Icons.error_outline, size: 42),
                SizedBox(height: 12),
                Text(
                  'Could not load games. Pull to retry.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          final games = snapshot.data ?? const [];
          if (games.isEmpty) {
            return ListView(
              padding: const EdgeInsets.all(24),
              children: const [
                SizedBox(height: 120),
                Icon(Icons.sports_esports_outlined, size: 46),
                SizedBox(height: 12),
                Text(
                  'No games yet. Import PGN games from the web client to start building your coaching history.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: games.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final game = games[index];
              return Card(
                child: ListTile(
                  title: Text(
                    '${game['white'] ?? 'White'} vs ${game['black'] ?? 'Black'}',
                  ),
                  subtitle: Text(
                    '${game['opening'] ?? 'Opening not identified'}\n'
                    '${game['player_color'] ?? 'Player side unknown'} · '
                    '${game['analyzed'] == true ? 'Analyzed' : 'Queued'}',
                  ),
                  isThreeLine: true,
                  trailing: Text('${game['result'] ?? '*'}'),
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => GameReviewScreen(
                          gameId: game['id'] as String,
                          title:
                              '${game['white'] ?? 'White'} vs ${game['black'] ?? 'Black'}',
                          playerColor: game['player_color'] as String?,
                        ),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class GameReviewScreen extends ConsumerStatefulWidget {
  const GameReviewScreen({
    required this.gameId,
    required this.title,
    this.playerColor,
    super.key,
  });

  final String gameId;
  final String title;
  final String? playerColor;

  @override
  ConsumerState<GameReviewScreen> createState() => _GameReviewScreenState();
}

class _GameReviewScreenState extends ConsumerState<GameReviewScreen> {
  late final Future<List<dynamic>> _future;
  int _selectedMove = 0;
  bool _flipped = false;

  @override
  void initState() {
    super.initState();
    final api = ref.read(apiClientProvider);
    _future = Future.wait<dynamic>([
      api.getJson('/games/${widget.gameId}/analysis'),
      api.getJson('/games/${widget.gameId}/mistakes'),
    ]);
  }

  int _moveIndexById(List<dynamic> moves, String? moveId) {
    if (moveId == null) return -1;
    return moves.indexWhere((raw) {
      final move = Map<String, dynamic>.from(raw as Map);
      return move['move_id'] == moveId;
    });
  }

  String _evaluation(Map<dynamic, dynamic>? engine, String key) {
    if (engine == null) return '—';
    final value = engine[key];
    if (value == null) return '—';
    return ((value as num) / 100).toStringAsFixed(2);
  }

  List<ChessBoardArrow> _arrows(
    BuildContext context,
    Map<String, dynamic> move,
  ) {
    final arrows = <ChessBoardArrow>[];
    final played = move['uci'] as String?;
    final engine = move['analysis'] as Map?;
    final best = engine?['best_move'] as String?;

    if (played != null && played.length >= 4) {
      arrows.add(
        ChessBoardArrow(
          from: played.substring(0, 2),
          to: played.substring(2, 4),
          color: Theme.of(context).colorScheme.error,
        ),
      );
    }
    if (best != null && best.length >= 4 && best != played) {
      arrows.add(
        ChessBoardArrow(
          from: best.substring(0, 2),
          to: best.substring(2, 4),
          color: Theme.of(context).colorScheme.primary,
        ),
      );
    }
    return arrows;
  }

  void _jumpToMove(int index, int total) {
    if (total == 0) return;
    setState(() {
      _selectedMove = index.clamp(0, total - 1);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return const Center(child: Text('Unable to load this game review.'));
          }

          final analysis =
              Map<String, dynamic>.from(snapshot.data![0] as Map);
          final moves = (analysis['moves'] as List?) ?? const [];
          final mistakes = (snapshot.data![1] as List?) ?? const [];
          if (moves.isEmpty) {
            return const Center(
              child: Text('No moves are available for this game yet.'),
            );
          }

          final selected = _selectedMove.clamp(0, moves.length - 1);
          final move = Map<String, dynamic>.from(moves[selected] as Map);
          final engine = move['analysis'] as Map?;
          final previousUci = selected > 0
              ? Map<String, dynamic>.from(moves[selected - 1] as Map)['uci']
                  as String?
              : null;
          final defaultWhiteAtBottom = widget.playerColor != 'black';
          final whiteAtBottom =
              _flipped ? !defaultWhiteAtBottom : defaultWhiteAtBottom;

          return ListView(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 28),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Decision ${selected + 1} of ${moves.length}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Flip board',
                    onPressed: () => setState(() => _flipped = !_flipped),
                    icon: const Icon(Icons.swap_vert),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              AspectRatio(
                aspectRatio: 1,
                child: ChessPositionBoard(
                  fen: move['fen_before'] as String,
                  whiteAtBottom: whiteAtBottom,
                  lastMoveUci: previousUci,
                  arrows: _arrows(context, move),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    tooltip: 'First move',
                    onPressed: selected == 0
                        ? null
                        : () => _jumpToMove(0, moves.length),
                    icon: const Icon(Icons.first_page),
                  ),
                  IconButton(
                    tooltip: 'Previous move',
                    onPressed: selected == 0
                        ? null
                        : () => _jumpToMove(selected - 1, moves.length),
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    child: Text(
                      '${move['ply']}. ${move['san']}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Next move',
                    onPressed: selected >= moves.length - 1
                        ? null
                        : () => _jumpToMove(selected + 1, moves.length),
                    icon: const Icon(Icons.chevron_right),
                  ),
                  IconButton(
                    tooltip: 'Last move',
                    onPressed: selected >= moves.length - 1
                        ? null
                        : () => _jumpToMove(moves.length - 1, moves.length),
                    icon: const Icon(Icons.last_page),
                  ),
                ],
              ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              engine?['classification'] as String? ??
                                  'Pending analysis',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                          if (engine?['cpl'] != null)
                            Chip(label: Text('CPL ${engine!['cpl']}')),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 16,
                        runSpacing: 8,
                        children: [
                          Text(
                            'Before: ${_evaluation(engine, 'before_cp')}',
                          ),
                          Text(
                            'After: ${_evaluation(engine, 'after_cp')}',
                          ),
                          Text(
                            'Played: ${move['uci']}',
                          ),
                          Text(
                            'Best: ${engine?['best_move'] ?? '—'}',
                          ),
                        ],
                      ),
                      if (engine?['pv'] != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          'Engine line: ${engine!['pv']}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Container(
                            width: 18,
                            height: 4,
                            color: Theme.of(context).colorScheme.error,
                          ),
                          const SizedBox(width: 6),
                          const Text('Played move'),
                          const SizedBox(width: 16),
                          Container(
                            width: 18,
                            height: 4,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(width: 6),
                          const Text('Engine move'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                'Critical moments',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              if (mistakes.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No persisted critical mistakes for this game.'),
                  ),
                )
              else
                ...mistakes.take(8).map((raw) {
                  final mistake = Map<String, dynamic>.from(raw as Map);
                  final ai = mistake['ai_coach'] as Map?;
                  final mistakeIndex =
                      _moveIndexById(moves, mistake['move_id'] as String?);
                  return Card(
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: mistakeIndex < 0
                          ? null
                          : () => _jumpToMove(mistakeIndex, moves.length),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    (mistake['category'] as String)
                                        .replaceAll('_', ' '),
                                    style:
                                        Theme.of(context).textTheme.titleMedium,
                                  ),
                                ),
                                if (mistakeIndex >= 0)
                                  Text('Move ${mistakeIndex + 1}'),
                              ],
                            ),
                            const SizedBox(height: 6),
                            if (mistake['explanation'] != null)
                              Text(mistake['explanation'] as String),
                            if (ai != null && ai['explanation'] != null) ...[
                              const Divider(height: 24),
                              Text(
                                'AI coach',
                                style: Theme.of(context).textTheme.labelLarge,
                              ),
                              const SizedBox(height: 4),
                              Text(ai['explanation'] as String),
                              if (ai['coaching_tip'] != null)
                                Text('Tip: ${ai['coaching_tip']}'),
                            ],
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              const SizedBox(height: 18),
              Text(
                'Move list',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              ...List.generate(moves.length, (index) {
                final row = Map<String, dynamic>.from(moves[index] as Map);
                final rowEngine = row['analysis'] as Map?;
                return ListTile(
                  selected: index == selected,
                  onTap: () => _jumpToMove(index, moves.length),
                  dense: true,
                  leading: CircleAvatar(child: Text('${row['ply']}')),
                  title: Text('${row['san']}'),
                  subtitle: rowEngine == null
                      ? const Text('Pending analysis')
                      : Text(
                          '${rowEngine['classification']} · '
                          'CPL ${rowEngine['cpl'] ?? '—'} · '
                          'best ${rowEngine['best_move'] ?? '—'}',
                        ),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}
