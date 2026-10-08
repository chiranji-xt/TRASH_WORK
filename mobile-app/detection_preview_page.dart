import 'dart:io';
import 'package:flutter/material.dart';

class DetectionPreviewPage extends StatelessWidget {
	const DetectionPreviewPage({super.key, required this.imageFile});

	final File imageFile;

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Detection Preview')),
			body: Stack(
				children: [
					Positioned.fill(
						child: Image.file(imageFile, fit: BoxFit.cover),
					),
					// Mock overlay
					Positioned(
						top: 48,
						left: 24,
						child: Container(
							padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
							decoration: BoxDecoration(
								border: Border.all(color: Colors.redAccent, width: 2),
								borderRadius: BorderRadius.circular(6),
								color: Colors.redAccent.withOpacity(0.12),
							),
							child: const Text('Mock: Object', style: TextStyle(color: Colors.white)),
						),
					),
				],
			),
			bottomNavigationBar: SafeArea(
				child: Padding(
					padding: const EdgeInsets.all(16),
					child: Row(
						children: [
							Expanded(
								child: OutlinedButton.icon(
									onPressed: () => Navigator.of(context).pop(),
									icon: const Icon(Icons.close),
									label: const Text('Retake'),
								),
							),
							const SizedBox(width: 12),
							Expanded(
								child: FilledButton.icon(
									onPressed: () {
										ScaffoldMessenger.of(context).showSnackBar(
											const SnackBar(content: Text('Saved mock detection')),
										);
									},
									icon: const Icon(Icons.save),
									label: const Text('Save'),
								),
							),
						],
					),
				),
			),
		);
	}
}
