import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';

class DashboardBundle {
  const DashboardBundle({
    required this.analytics,
    required this.training,
    required this.games,
    required this.syncedOfflineAttempts,
  });

  final Map<String, dynamic> analytics;
  final Map<String, dynamic> training;
  final List<Map<String, dynamic>> games;
  final int syncedOfflineAttempts;
}

class CoachDashboard extends ConsumerStatefulWidget {
  const CoachDashboard({super.key});

  @override
  ConsumerState<CoachDashboard> createState() => _CoachDashboardState();
}

class _CoachDashboardState extends ConsumerState<CoachDashboard> {
  late Future<DashboardBundle> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<DashboardBundle> _load() async {
    final api = ref.read(apiClientProvider);
    final synced = await api.syncPendingPuzzleAttempts();
    final values = await Future.wait<dynamic>([
      api.cachedGet('/analytics', cacheKey: 'mobile_cache_analytics'),
      api.cachedGet('/training', cacheKey: 'mobile_cache_training'),
      api.cachedGet('/games?limit=4', cacheKey: 'mobile_cache_recent_games'),
    ]);
    return DashboardBundle(
      analytics: Map<String, dynamic>.from(values[0] as Map),
      training: Map<String, dynamic>.from(values[1] as Map),
      games: (values[2] as List<dynamic>)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
      syncedOfflineAttempts: synced,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<DashboardBundle>(
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
          if (snapshot.hasError || !snapshot.hasData) {
            return ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const SizedBox(height: 120),
                const Icon(Icons.cloud_off, size: 46),
                const SizedBox(height: 12),
                Text(
                  'Unable to load your coaching dashboard.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Pull to retry. Cached data is used automatically when available.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }

          final data = snapshot.data!;
          final overview = Map<String, dynamic>.from(
            (data.analytics['overview'] as Map?) ?? const {},
          );
          final weaknesses = (data.analytics['weaknesses'] as List?) ?? const [];
          final insights = (data.analytics['insights'] as List?) ?? const [];
          final sessions = (data.training['sessions'] as List?) ?? const [];
          final dueReviews = data.training['due_reviews'] ?? 0;
          final topWeakness = weaknesses.isEmpty
              ? null
              : Map<String, dynamic>.from(weaknesses.first as Map);
          final topInsight = insights.isEmpty
              ? null
              : Map<String, dynamic>.from(insights.first as Map);
          Map<String, dynamic>? nextSession;
          for (final raw in sessions) {
            final session = Map<String, dynamic>.from(raw as Map);
            if (session['completed_at'] == null) {
              nextSession = session;
              break;
            }
          }

          return ListView(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 28),
            children: [
              Text(
                'CURRENT COACHING FOCUS',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      letterSpacing: 1.1,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                topInsight?['title'] as String? ??
                    (topWeakness?['category'] as String?)
                        ?.replaceAll('_', ' ') ??
                    'Import more games to build your player profile.',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                topInsight?['body'] as String? ??
                    (topWeakness == null
                        ? 'ChessCoach waits for enough evidence before calling something a recurring weakness.'
                        : 'This theme is supported by ${topWeakness['sample_size']} detected examples.'),
              ),
              if (data.syncedOfflineAttempts > 0) ...[
                const SizedBox(height: 12),
                _InfoChip(
                  icon: Icons.sync,
                  text:
                      '${data.syncedOfflineAttempts} offline puzzle attempt(s) synced',
                ),
              ],
              const SizedBox(height: 22),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _MetricCard(
                    label: 'Rating',
                    value: '${data.analytics['rating'] ?? '—'}',
                  ),
                  _MetricCard(
                    label: 'Analyzed games',
                    value: '${overview['games_analyzed'] ?? 0}',
                  ),
                  _MetricCard(
                    label: 'Accuracy',
                    value: overview['accuracy'] == null
                        ? '—'
                        : '${(overview['accuracy'] as num).toStringAsFixed(1)}%',
                  ),
                  _MetricCard(
                    label: 'Due puzzles',
                    value: '$dueReviews',
                  ),
                ],
              ),
              const SizedBox(height: 22),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Next training session'),
                      const SizedBox(height: 6),
                      Text(
                        nextSession == null
                            ? 'No unfinished session right now'
                            : (nextSession['type'] as String)
                                .replaceAll('_', ' '),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      if (nextSession?['focus_category'] != null)
                        Text(
                          (nextSession!['focus_category'] as String)
                              .replaceAll('_', ' '),
                        ),
                      if (nextSession != null)
                        Text('Target: ${nextSession['target_count']}'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 22),
              Text(
                'Recent games',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              if (data.games.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(18),
                    child: Text('No imported games yet.'),
                  ),
                )
              else
                ...data.games.map(
                  (game) => Card(
                    child: ListTile(
                      title: Text(
                        '${game['white'] ?? 'White'} vs ${game['black'] ?? 'Black'}',
                      ),
                      subtitle: Text(
                        '${game['opening'] ?? 'Opening not identified'} · '
                        '${game['analyzed'] == true ? 'Analyzed' : 'Queued'}',
                      ),
                      trailing: Text('${game['result'] ?? '*'}'),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label),
              const SizedBox(height: 6),
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(text)),
      ],
    );
  }
}
