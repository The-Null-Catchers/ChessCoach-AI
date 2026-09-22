import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';

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
            return const ListView(
              padding: EdgeInsets.all(24),
              children: [
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

class GameReviewScreen extends ConsumerWidget {
  const GameReviewScreen({
    required this.gameId,
    required this.title,
    super.key,
  });

  final String gameId;
  final String title;

  Future<List<dynamic>> _load(WidgetRef ref) {
    final api = ref.read(apiClientProvider);
    return Future.wait<dynamic>([
      api.getJson('/games/$gameId/analysis'),
      api.getJson('/games/$gameId/mistakes'),
    ]);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: FutureBuilder<List<dynamic>>(
        future: _load(ref),
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

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
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
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            (mistake['category'] as String)
                                .replaceAll('_', ' '),
                            style: Theme.of(context).textTheme.titleMedium,
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
                  );
                }),
              const SizedBox(height: 18),
              Text(
                'Move analysis',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              ...moves.map((raw) {
                final move = Map<String, dynamic>.from(raw as Map);
                final engine = move['analysis'] as Map?;
                return ListTile(
                  dense: true,
                  leading: CircleAvatar(child: Text('${move['ply']}')),
                  title: Text('${move['san']}'),
                  subtitle: engine == null
                      ? const Text('Pending analysis')
                      : Text(
                          '${engine['classification']} · '
                          'CPL ${engine['cpl'] ?? '—'} · '
                          'best ${engine['best_move'] ?? '—'}',
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
