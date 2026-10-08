import 'package:flutter/material.dart';
import 'dart:io';
import 'report_store.dart';

class ReportDetailsPage extends StatelessWidget {
	const ReportDetailsPage({super.key, required this.item});

	final ReportItem item;

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Report Details'),
				actions: [
					IconButton(
						icon: const Icon(Icons.delete_outline),
						onPressed: () {
							reportStore.remove(item.id);
							Navigator.of(context).pop();
							ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Report deleted')));
						},
						tooltip: 'Delete',
					),
				],
			),
			body: ListView(
				padding: const EdgeInsets.all(16),
				children: [
					if (item.imageFile != null)
						ClipRRect(
							borderRadius: BorderRadius.circular(12),
							child: Image.file(item.imageFile!, height: 220, fit: BoxFit.cover),
						)
					else if (item.imageUrl != null)
						ClipRRect(
							borderRadius: BorderRadius.circular(12),
							child: Image.network(item.imageUrl!, height: 220, fit: BoxFit.cover),
						),
					const SizedBox(height: 12),
					Text(item.title, style: Theme.of(context).textTheme.headlineSmall),
					const SizedBox(height: 8),
					Wrap(spacing: 8, children: [
						Chip(label: Text(item.category)),
						Chip(label: Text('Severity ${item.severity}')),
						if (item.includeLocation) const Chip(label: Text('Location attached')),
					]),
					const SizedBox(height: 8),
					Text(item.description),
					const SizedBox(height: 16),
					Text('Submitted ${_timeAgo(item.createdAt)}', style: Theme.of(context).textTheme.bodySmall),
				],
			),
		);
	}

	String _timeAgo(DateTime dt) {
		final d = DateTime.now().difference(dt);
		if (d.inSeconds < 60) return '${d.inSeconds}s ago';
		if (d.inMinutes < 60) return '${d.inMinutes}m ago';
		if (d.inHours < 24) return '${d.inHours}h ago';
		return '${d.inDays}d ago';
	}
}
