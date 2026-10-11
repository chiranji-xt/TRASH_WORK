import 'package:flutter/material.dart';

import 'report_store.dart' show getApiKey, setApiKey;

class SettingsPage extends StatefulWidget {
	const SettingsPage({super.key, this.onChangeTheme});

	final void Function(ThemeMode mode)? onChangeTheme;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _keyController = TextEditingController();
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    getApiKey().then((k) {
      if (mounted) {
        setState(() {
          _keyController.text = k ?? '';
          _loaded = true;
        });
      }
    });
  }

  @override
  void dispose() {
    _keyController.dispose();
    super.dispose();
  }

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
								Text('Crew access', style: Theme.of(context).textTheme.titleMedium),
								const SizedBox(height: 4),
								const Text('Admin or cleaner API key. Cleaners can verify cleanups; only admins can change status.'),
								const SizedBox(height: 8),
								TextField(
									controller: _keyController,
									obscureText: true,
									enableSuggestions: false,
									autocorrect: false,
									decoration: const InputDecoration(
										border: OutlineInputBorder(),
										labelText: 'API key',
										hintText: 'demo-admin-key / demo-cleaner-key',
									),
								),
								const SizedBox(height: 8),
								Row(
									children: [
										FilledButton(
											onPressed: () async {
												await setApiKey(_keyController.text);
												if (context.mounted) {
													ScaffoldMessenger.of(context).showSnackBar(
														const SnackBar(content: Text('API key saved')));
												}
											},
											child: const Text('Save'),
										),
										const SizedBox(width: 8),
										TextButton(
											onPressed: () async {
												await setApiKey(null);
												_keyController.clear();
												if (context.mounted) {
													ScaffoldMessenger.of(context).showSnackBar(
														const SnackBar(content: Text('API key cleared')));
												}
											},
											child: const Text('Clear'),
										),
									],
								),
								if (!_loaded)
									const Padding(
										padding: EdgeInsets.only(top: 4),
										child: Text('Loading saved key…'),
									),
							],
						),
					),
				),
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
											onSelected: (_) => widget.onChangeTheme?.call(ThemeMode.system),
										),
										ChoiceChip(
											label: const Text('Light'),
											selected: current == ThemeMode.light,
											onSelected: (_) => widget.onChangeTheme?.call(ThemeMode.light),
										),
										ChoiceChip(
											label: const Text('Dark'),
											selected: current == ThemeMode.dark,
											onSelected: (_) => widget.onChangeTheme?.call(ThemeMode.dark),
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
