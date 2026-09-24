import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../widgets/chess_board.dart';

class OpeningsScreen extends ConsumerStatefulWidget {
  const OpeningsScreen({super.key});

  @override
  ConsumerState<OpeningsScreen> createState() => _OpeningsScreenState();
}

class _OpeningsScreenState extends ConsumerState<OpeningsScreen> {
  List<Map<String, dynamic>> _repertoires = const [];
  List<Map<String, dynamic>> _training = const [];
  String? _selectedId;
  String? _candidateMove;
  bool _loading = true;
  bool _submitting = false;
  String? _message;
  int _boardRevision = 0;

  Map<String, dynamic>? get _selected {
    for (final item in _repertoires) {
      if (item['id'] == _selectedId) return item;
    }
    return null;
  }

  Map<String, dynamic>? get _current =>
      _training.isEmpty ? null : _training.first;

  @override
  void initState() {
    super.initState();
    Future<void>.microtask(_loadRepertoires);
  }

  Future<void> _loadRepertoires({String? preferredId}) async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final raw = await api.cachedGet(
        '/repertoires',
        cacheKey: 'opening_repertoires',
      );
      final items = (raw as List<dynamic>)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(growable: false);
      final nextId = preferredId ??
          _selectedId ??
          (items.isEmpty ? null : items.first['id'] as String);
      if (!mounted) return;
      setState(() {
        _repertoires = items;
        _selectedId = nextId;
        _loading = false;
      });
      if (nextId != null) {
        await _loadTraining(nextId);
      } else {
        setState(() => _training = const []);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _message = 'Could not load opening repertoires.';
      });
    }
  }

  Future<void> _loadTraining(String repertoireId) async {
    try {
      final raw = await ref.read(apiClientProvider).cachedGet(
            '/repertoires/$repertoireId/training?limit=30',
            cacheKey: 'opening_training_$repertoireId',
          );
      final items = (raw as List<dynamic>)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(growable: false);
      if (!mounted) return;
      setState(() {
        _training = items;
        _candidateMove = null;
        _boardRevision += 1;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _message = 'Could not load opening training.');
    }
  }

  Future<void> _createRepertoire() async {
    final nameController = TextEditingController();
    var color = 'white';
    final created = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('New repertoire'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  hintText: 'Italian Game',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: color,
                decoration: const InputDecoration(labelText: 'Color'),
                items: const [
                  DropdownMenuItem(value: 'white', child: Text('White')),
                  DropdownMenuItem(value: 'black', child: Text('Black')),
                ],
                onChanged: (value) {
                  if (value != null) setDialogState(() => color = value);
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
    if (created != true || nameController.text.trim().isEmpty) return;

    try {
      final response = await ref.read(apiClientProvider).postJson(
        '/repertoires',
        data: {
          'name': nameController.text.trim(),
          'color': color,
        },
      );
      final id = (response as Map)['id'] as String;
      await _loadRepertoires(preferredId: id);
    } catch (_) {
      if (mounted) {
        setState(() => _message = 'Could not create repertoire.');
      }
    }
  }

  Future<void> _importPgn() async {
    final id = _selectedId;
    if (id == null) return;
    final controller = TextEditingController();
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Import repertoire PGN'),
        content: SizedBox(
          width: 520,
          child: TextField(
            controller: controller,
            minLines: 8,
            maxLines: 14,
            decoration: const InputDecoration(
              hintText: 'Paste PGN including variations…',
              alignLabelWithHint: true,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Import'),
          ),
        ],
      ),
    );
    if (accepted != true || controller.text.trim().isEmpty) return;

    try {
      final response = await ref.read(apiClientProvider).postJson(
        '/repertoires/$id/import-pgn',
        data: {'pgn': controller.text},
      );
      final count = (response as Map)['imported_nodes'];
      if (!mounted) return;
      setState(() => _message = 'Imported $count new move-tree nodes.');
      await _loadRepertoires(preferredId: id);
    } catch (_) {
      if (mounted) setState(() => _message = 'PGN import failed.');
    }
  }

  Future<void> _submitGrade(String grade) async {
    final id = _selectedId;
    final current = _current;
    final move = _candidateMove;
    if (id == null || current == null || move == null || _submitting) return;

    setState(() => _submitting = true);
    try {
      final result = Map<String, dynamic>.from(
        await ref.read(apiClientProvider).postJson(
              '/repertoires/$id/lines/${current['line_id']}/attempt',
              data: {'move_uci': move, 'grade': grade},
            ) as Map,
      );
      if (!mounted) return;
      final correct = result['correct'] == true;
      final expectedSan = result['expected_move_san'];
      final expectedUci = result['expected_move_uci'];
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(correct ? 'Correct' : 'Review this line'),
          content: Text(
            correct
                ? 'Mastery ${result['mastery']}%'
                : 'Expected $expectedSan ($expectedUci).',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Next'),
            ),
          ],
        ),
      );
      if (mounted) await _loadRepertoires(preferredId: id);
    } catch (_) {
      if (mounted) {
        setState(() {
          _candidateMove = null;
          _boardRevision += 1;
          _message = 'Could not submit this opening attempt.';
        });
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _repertoires.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    final selected = _selected;
    final current = _current;
    final color = selected?['color'] as String? ?? 'white';

    return RefreshIndicator(
      onRefresh: () => _loadRepertoires(preferredId: _selectedId),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Opening repertoire',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              IconButton(
                tooltip: 'New repertoire',
                onPressed: _createRepertoire,
                icon: const Icon(Icons.add_circle_outline),
              ),
              IconButton(
                tooltip: 'Import PGN',
                onPressed: selected == null ? null : _importPgn,
                icon: const Icon(Icons.upload_file_outlined),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Train your own move trees with spaced repetition.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!),
          ],
          const SizedBox(height: 16),
          if (_repertoires.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    const Text('No opening repertoire yet.'),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: _createRepertoire,
                      icon: const Icon(Icons.add),
                      label: const Text('Create repertoire'),
                    ),
                  ],
                ),
              ),
            )
          else ...[
            DropdownButtonFormField<String>(
              initialValue: _selectedId,
              decoration: const InputDecoration(labelText: 'Repertoire'),
              items: [
                for (final item in _repertoires)
                  DropdownMenuItem(
                    value: item['id'] as String,
                    child: Text(
                      '${item['name']} · ${item['color']} · ${item['due']} due',
                    ),
                  ),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() => _selectedId = value);
                _loadTraining(value);
              },
            ),
            if (selected != null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Chip(label: Text('${selected['lines']} nodes')),
                  Chip(label: Text('${selected['trainable']} trainable')),
                  Chip(label: Text('${selected['due']} due')),
                  Chip(label: Text('${selected['mastery']}% mastery')),
                ],
              ),
            ],
            const SizedBox(height: 18),
            if (current == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No opening moves are due right now.'),
                ),
              )
            else ...[
              Text(
                'Find your repertoire move',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 4),
              Text(
                'Ply ${current['ply']} · ${current['mastery']}% mastery · ${current['lapses']} lapses',
              ),
              const SizedBox(height: 14),
              AspectRatio(
                aspectRatio: 1,
                child: ChessPositionBoard(
                  key: ValueKey('${current['line_id']}-$_boardRevision'),
                  fen: current['fen'] as String,
                  whiteAtBottom: color == 'white',
                  enabled: _candidateMove == null && !_submitting,
                  onMove: (uci) async {
                    if (mounted) setState(() => _candidateMove = uci);
                  },
                ),
              ),
              const SizedBox(height: 12),
              if (_candidateMove == null)
                const Text('Tap or drag a piece to make your move.')
              else ...[
                Text('Selected move: $_candidateMove'),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: _submitting ? null : () => _submitGrade('again'),
                      child: const Text('Again'),
                    ),
                    OutlinedButton(
                      onPressed: _submitting ? null : () => _submitGrade('hard'),
                      child: const Text('Hard'),
                    ),
                    FilledButton.tonal(
                      onPressed: _submitting ? null : () => _submitGrade('good'),
                      child: const Text('Good'),
                    ),
                    FilledButton(
                      onPressed: _submitting ? null : () => _submitGrade('easy'),
                      child: const Text('Easy'),
                    ),
                  ],
                ),
              ],
            ],
          ],
        ],
      ),
    );
  }
}
