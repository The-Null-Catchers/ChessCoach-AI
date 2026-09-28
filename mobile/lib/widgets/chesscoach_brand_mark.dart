import 'package:flutter/material.dart';

class ChessCoachBrandMark extends StatelessWidget {
  const ChessCoachBrandMark({
    super.key,
    this.size = 48,
  });

  final double size;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.24),
        color: scheme.surfaceContainerHighest,
        border: Border.all(
          color: scheme.primary.withValues(alpha: 0.45),
          width: size * 0.035,
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Text(
            '♞',
            style: TextStyle(
              fontSize: size * 0.64,
              height: 1,
              fontWeight: FontWeight.w700,
              color: scheme.onSurface,
            ),
          ),
          Positioned(
            right: size * 0.08,
            top: size * 0.08,
            child: Container(
              width: size * 0.13,
              height: size * 0.13,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: scheme.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
