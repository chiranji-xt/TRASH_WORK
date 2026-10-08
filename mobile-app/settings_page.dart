import 'package:flutter/material.dart';

class SettingsPage extends StatelessWidget {
	const SettingsPage({super.key, this.onChangeTheme});

	final void Function(ThemeMode mode)? onChangeTheme;

	@override
	Widget build(BuildContext context) {
		ThemeMode current = ThemeMode.system;
		return ListView(
			padding: const EdgeInsets.all(16),
			children: [
				Text('Settings', style: Theme.of(context).textTheme.headlineSmall),
				const SizedBox(height: 12),
				Card(
					child: Padding(
						padding: const EdgeInsets.all(12),
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Text('Theme', style: Theme.of(context).textTheme.titleMedium),
								const SizedBox(height: 8),
								Wrap(
									spacing: 8,
									runSpacing: 8,
									children: [
										ChoiceChip(
											label: const Text('System'),
											selected: current == ThemeMode.system,
											onSelected: (_) => onChangeTheme?.call(ThemeMode.system),
										),
										ChoiceChip(
											label: const Text('Light'),
											selected: current == ThemeMode.light,
											onSelected: (_) => onChangeTheme?.call(ThemeMode.light),
										),
										ChoiceChip(
											label: const Text('Dark'),
											selected: current == ThemeMode.dark,
											onSelected: (_) => onChangeTheme?.call(ThemeMode.dark),
										),
									],
								),
							],
						),
					),
				),
			],
		);
	}
}
