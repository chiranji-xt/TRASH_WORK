import 'package:flutter/material.dart';
import 'dart:io';
import 'report_store.dart';
import 'verify_cleanup_page.dart';

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
				Wrap(spacing: 8, runSpacing: 8, children: [
					Chip(label: Text(item.category)),
					Chip(label: Text('Severity ${item.severity}')),
					if (item.includeLocation) const Chip(label: Text('Location attached')),
					if (item.caseId != null)
						Chip(
							avatar: const Icon(Icons.folder_copy_outlined, size: 16),
							label: Text('Case #${item.caseId}'),
						),
				]),
				if (item.prediction != null && item.prediction!.isNotEmpty) ...[
					const SizedBox(height: 12),
					Row(
						children: [
							Expanded(
								child: Text(
									item.prediction!,
									style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
								),
							),
							if (item.confidence != null)
								Text('${(item.confidence! * 100).toStringAsFixed(1)}%', style: Theme.of(context).textTheme.bodyMedium),
						],
					),
					if (item.confidence != null) ...[
						const SizedBox(height: 6),
						LinearProgressIndicator(value: item.confidence!.clamp(0.0, 1.0)),
					],
				],
				if (item.detections.isNotEmpty) ...[
					const SizedBox(height: 12),
					Text(
						'All detections · ${item.detections.length}',
						style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
					),
					const SizedBox(height: 6),
					...item.detections.map((d) => Padding(
						padding: const EdgeInsets.only(bottom: 8),
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Row(
									children: [
										Expanded(child: Text(d.className, style: Theme.of(context).textTheme.bodyMedium)),
										Text('${(d.confidence * 100).toStringAsFixed(0)}%', style: Theme.of(context).textTheme.bodySmall),
									],
								),
								const SizedBox(height: 4),
								LinearProgressIndicator(value: d.confidence.clamp(0.0, 1.0)),
							],
						),
					)),
				],
				if (item.boxedImageUrl != null) ...[
					const SizedBox(height: 12),
					Text('AI detection overlay', style: Theme.of(context).textTheme.labelLarge),
					const SizedBox(height: 6),
					ClipRRect(
						borderRadius: BorderRadius.circular(12),
						child: Image.network(item.boxedImageUrl!, height: 220, fit: BoxFit.cover),
					),
				],
				const SizedBox(height: 8),
				Text(item.description),
				const SizedBox(height: 16),
				if (item.caseId != null)
					FilledButton.icon(
						onPressed: () {
							Navigator.of(context).push(
								MaterialPageRoute(
									builder: (_) => VerifyCleanupPage(caseId: item.caseId!),
								),
							);
						},
						icon: const Icon(Icons.verified_outlined),
						label: Text('Verify cleanup · Case #${item.caseId}'),
					),
				if (item.caseId != null) const SizedBox(height: 8),
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
