import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';

class TrainingScreen extends ConsumerStatefulWidget {
  const TrainingScreen({super.key});

  @override
  ConsumerState<TrainingScreen> createState() => _TrainingScreenState();
}

class _TrainingScreenState extends ConsumerState<TrainingScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final data = await ref
        .read(apiClientProvider)
        .cachedGet('/training', cacheKey: 'mobile_cache_training');
    return Map<String, dynamic>.from(data as Map);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _complete(String id) async {
    await ref.read(apiClientProvider).postJson(
      '/training/$id/complete',
      data: {'minutes_spent': 15},
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Training session completed')),
    );
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<Map<String, dynamic>>(
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
            return const ListView(
              padding: EdgeInsets.all(24),
              children: [
                SizedBox(height: 120),
                Text(
                  'Unable to load the training plan. Pull to retry.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }

          final data = snapshot.data!;
          final plan = Map<String, dynamic>.from(
            (data['plan'] as Map?) ?? const {},
          );
          final sessions = (data['sessions'] as List?) ?? const [];

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'Weekly plan',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 6),
              Text(
                plan['focus_summary'] as String? ??
                    'Your plan will adapt as more evidence is collected.',
              ),
              const SizedBox(height: 6),
              Text('${data['due_reviews'] ?? 0} spaced-repetition reviews due'),
              const SizedBox(height: 18),
              ...sessions.map((raw) {
                final session = Map<String, dynamic>.from(raw as Map);
                final complete = session['completed_at'] != null;
                return Card(
                  child: ListTile(
                    leading: Icon(
                      complete
                          ? Icons.check_circle
                          : Icons.radio_button_unchecked,
                    ),
                    title: Text(
                      (session['type'] as String).replaceAll('_', ' '),
                    ),
                    subtitle: Text(
                      '${(session['focus_category'] as String?)?.replaceAll('_', ' ') ?? 'Mixed improvement'} · '
                      'target ${session['target_count']}',
                    ),
                    trailing: complete
                        ? Text('${session['minutes_spent']} min')
                        : FilledButton.tonal(
                            onPressed: () => _complete(session['id'] as String),
                            child: const Text('Done'),
                          ),
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
