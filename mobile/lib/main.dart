import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() => runApp(const ProviderScope(child: ChessCoachApp()));

class ChessCoachApp extends StatelessWidget {
  const ChessCoachApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    themeMode: ThemeMode.dark,
    darkTheme: ThemeData.dark(useMaterial3: true).copyWith(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFD8FF78), brightness: Brightness.dark),
      scaffoldBackgroundColor: const Color(0xFF111511),
    ),
    home: const DashboardScreen(),
  );
}

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ChessCoach AI')),
    body: ListView(padding: const EdgeInsets.all(18), children: [
      Text('Today’s coaching focus', style: Theme.of(context).textTheme.labelLarge?.copyWith(color: Theme.of(context).colorScheme.primary)),
      const SizedBox(height: 8),
      Text('Stop weakening your king before development is complete.', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 12),
      const Text('Your training queue prioritizes recurring mistakes from your own games, weighted by severity, confidence, recency and spaced repetition.'),
      const SizedBox(height: 20),
      FilledButton(onPressed: () {}, child: const Text('Start today’s training')),
      const SizedBox(height: 24),
      const Wrap(spacing: 12, runSpacing: 12, children: [
        _Stat('Rating','1460'), _Stat('Games','124'), _Stat('Tactical','73%'), _Stat('Streak','6 days')
      ]),
    ]),
    bottomNavigationBar: NavigationBar(selectedIndex: 0, destinations: const [
      NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Coach'),
      NavigationDestination(icon: Icon(Icons.sports_esports_outlined), label: 'Games'),
      NavigationDestination(icon: Icon(Icons.school_outlined), label: 'Train'),
      NavigationDestination(icon: Icon(Icons.insights_outlined), label: 'Analytics'),
    ]),
  );
}
class _Stat extends StatelessWidget { final String label,value; const _Stat(this.label,this.value); @override Widget build(BuildContext c)=>SizedBox(width:150,child:Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(label),const SizedBox(height:6),Text(value,style:Theme.of(c).textTheme.headlineSmall)]))));}
