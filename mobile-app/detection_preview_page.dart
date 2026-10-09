import 'dart:io';

import 'package:flutter/material.dart';

import 'config.dart';
import 'report_store.dart';

/// Detection preview: uploads the photo to POST /predict, then shows the
/// returned boxed image and detected class. Replaces the old mock overlay.
class DetectionPreviewPage extends StatefulWidget {
  const DetectionPreviewPage({
    super.key,
    required this.imageFile,
    this.latitude,
    this.longitude,
    this.category,
    this.severity,
    this.title,
    this.description,
  });

  final File imageFile;
  final double? latitude;
  final double? longitude;
  final String? category;
  final int? severity;
  final String? title;
  final String? description;

  @override
  State<DetectionPreviewPage> createState() => _DetectionPreviewPageState();
}

class _DetectionPreviewPageState extends State<DetectionPreviewPage> {
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _result;

  String? get _boxedUrl {
    final p = _result?['boxed_image_path']?.toString();
    if (p == null || p.isEmpty) return null;
    if (p.startsWith('http')) return p;
    return '$baseUrl${p.startsWith('/') ? p : '/$p'}';
  }

  Future<void> _detectAndUpload() async {
    final lat = widget.latitude;
    final lon = widget.longitude;
    if (lat == null || lon == null) {
      setState(() => _error = 'Location missing — submit from the Report tab with lat/lon.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await uploadReport(
        image: widget.imageFile,
        latitude: lat,
        longitude: lon,
        category: widget.category,
        severity: widget.severity,
        title: widget.title,
        description: widget.description,
      );
      if (!mounted) return;
      setState(() => _result = res);
      // Add to local history store.
      final dets = res['detections'];
      reportStore.add(ReportItem(
        id: res['report_id']?.toString() ?? DateTime.now().toIso8601String(),
        title: widget.title?.isNotEmpty == true ? widget.title! : 'Report ${res['report_id']}',
        description: res['prediction']?.toString() ?? 'Detected Waste',
        category: res['prediction']?.toString() ?? widget.category ?? 'Waste',
        severity: (res['severity'] as num?)?.toInt() ?? widget.severity ?? 3,
        includeLocation: true,
        imageFile: widget.imageFile,
        imageUrl: res['image_path']?.toString().startsWith('http') == true
            ? res['image_path'].toString()
            : '$baseUrl${res['image_path']}',
        boxedImageUrl: _boxedUrlFrom(res),
        prediction: res['prediction']?.toString(),
        confidence: (res['confidence'] as num?)?.toDouble(),
        latitude: lat,
        longitude: lon,
        status: kStatusPending,
      ));
      if (dets == null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Uploaded — no waste detected in this photo')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _boxedUrlFrom(Map<String, dynamic> res) {
    final p = res['boxed_image_path']?.toString();
    if (p == null || p.isEmpty) return null;
    if (p.startsWith('http')) return p;
    return '$baseUrl${p.startsWith('/') ? p : '/$p'}';
  }

  @override
  void initState() {
    super.initState();
    // Auto-run detection when lat/lon are provided (coming from Report tab).
    if (widget.latitude != null && widget.longitude != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _detectAndUpload());
    }
  }

  @override
  Widget build(BuildContext context) {
    final prediction = _result?['prediction']?.toString();
    final confidence = (_result?['confidence'] as num?)?.toDouble();
    final duplicateOf = _result?['duplicate_of'];

    return Scaffold(
      appBar: AppBar(title: const Text('Detection Preview')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(widget.imageFile, height: 240, fit: BoxFit.cover),
          ),
          const SizedBox(height: 12),
          if (_loading)
            const Center(child: CircularProgressIndicator())
          else if (_error != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red),
              ),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            )
          else if (_result != null) ...[
            if (_boxedUrl != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(_boxedUrl!, height: 240, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const SizedBox()),
              ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.verified, color: Colors.green),
              title: Text(prediction ?? 'Unknown'),
              subtitle: Text(confidence != null
                  ? 'Confidence ${(confidence * 100).toStringAsFixed(1)}% • Severity ${_result!['severity'] ?? '-'}'
                  : 'No confidence score'),
            ),
            if (duplicateOf != null)
              Chip(label: Text('Possible duplicate of report #$duplicateOf (within ~20 m)')),
          ] else
            const Text('Tap "Detect" to run the model on this photo.'),

          if (widget.latitude != null && widget.longitude != null)
            Text('Location: ${widget.latitude!.toStringAsFixed(5)}, ${widget.longitude!.toStringAsFixed(5)}',
                style: Theme.of(context).textTheme.bodySmall),
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
                  onPressed: _loading ? null : _detectAndUpload,
                  icon: const Icon(Icons.auto_fix_high),
                  label: Text(_result == null ? 'Detect' : 'Re-run'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
