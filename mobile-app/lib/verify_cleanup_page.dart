import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import 'report_store.dart';

/// Cleaner flow: photograph the cleaned site (1-3 after-photos) and submit
/// for verification. Shows the decision (passed / failed / needs review),
/// per-check evidence and annotated images.
///
/// HONEST LIMIT (also in the API): the detector cannot prove absence — a
/// missed detection can wrongly pass. Uncertain evidence goes to review.
class VerifyCleanupPage extends StatefulWidget {
  const VerifyCleanupPage({super.key, required this.caseId});

  final int caseId;

  @override
  State<VerifyCleanupPage> createState() => _VerifyCleanupPageState();
}

class _VerifyCleanupPageState extends State<VerifyCleanupPage> {
  final List<XFile> _photos = [];
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _result;

  Future<void> _pick(ImageSource source) async {
    if (_photos.length >= 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('At most 3 after-photos per attempt')));
      return;
    }
    final file = await ImagePicker().pickImage(source: source);
    if (file != null && mounted) setState(() => _photos.add(file));
  }

  Future<void> _submit() async {
    if (_photos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Take at least one after-photo first')));
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      double? lat;
      double? lon;
      if (perm != LocationPermission.denied &&
          perm != LocationPermission.deniedForever) {
        try {
          final pos = await Geolocator.getCurrentPosition();
          lat = pos.latitude;
          lon = pos.longitude;
        } catch (_) {/* fall through to error below */}
      }
      if (lat == null || lon == null) {
        throw const HttpException('Location unavailable — enable GPS and retry');
      }
      final res = await submitVerification(
        caseId: widget.caseId,
        images: [for (final p in _photos) File(p.path)],
        latitude: lat,
        longitude: lon,
        capturedAt: DateTime.now(),
      );
      if (mounted) setState(() => _result = res);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final decision = _result?['decision']?.toString();
    return Scaffold(
      appBar: AppBar(title: Text('Verify cleanup · Case #${widget.caseId}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Photograph the cleaned site. The backend checks location, capture '
            'time, photo reuse and runs the detector — the case closes only on a pass.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              FilledButton.icon(
                onPressed: _loading ? null : () => _pick(ImageSource.camera),
                icon: const Icon(Icons.camera_alt),
                label: const Text('Camera'),
              ),
              OutlinedButton.icon(
                onPressed: _loading ? null : () => _pick(ImageSource.gallery),
                icon: const Icon(Icons.photo_library),
                label: const Text('Gallery'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_photos.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('No after-photos yet (1–3 required).'),
              ),
            )
          else
            SizedBox(
              height: 110,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) => Stack(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.file(File(_photos[i].path),
                          width: 110, height: 110, fit: BoxFit.cover),
                    ),
                    Positioned(
                      right: 0,
                      top: 0,
                      child: IconButton(
                        icon: const Icon(Icons.close, size: 18),
                        color: Colors.white,
                        style: IconButton.styleFrom(
                            backgroundColor: Colors.black54),
                        onPressed: () =>
                            setState(() => _photos.removeAt(i)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Submit for verification'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          if (_result != null) ...[
            const SizedBox(height: 16),
            _DecisionCard(result: _result!),
          ],
        ],
      ),
    );
  }
}

class _DecisionCard extends StatelessWidget {
  const _DecisionCard({required this.result});

  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final decision = result['decision']?.toString() ?? 'unknown';
    final color = switch (decision) {
      'passed' => Colors.green,
      'failed_still_litter' => Colors.red,
      'rejected_reuse' => Colors.red,
      _ => Colors.orange,
    };
    final checks = (result['checks'] as List?) ?? const [];
    final annotated = (result['annotated_images'] as List?) ?? const [];
    final reasons = (result['needs_review_reasons'] as List?) ?? const [];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.verified_outlined, color: color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    decision.replaceAll('_', ' ').toUpperCase(),
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold, color: color),
                  ),
                ),
              ],
            ),
            if (reasons.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final r in reasons)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $r',
                      style: Theme.of(context).textTheme.bodySmall),
                ),
            ],
            const SizedBox(height: 8),
            Text('Checks', style: Theme.of(context).textTheme.titleSmall),
            for (final c in checks)
              if (c is Map)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Photo ${(c['photo_index'] as num? ?? 0) + 1}',
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                      _checkRow(context, 'Location',
                          (c['location'] as Map?)?['ok'] == true,
                          _detail((c['location'] as Map?))),
                      _checkRow(context, 'Capture time',
                          (c['time'] as Map?)?['ok'] == true,
                          _detail((c['time'] as Map?))),
                      _checkRow(context, 'Original photo',
                          (c['reuse'] as Map?)?['ok'] == true,
                          _detail((c['reuse'] as Map?))),
                      _checkRow(context, 'Detector',
                          (c['detection'] as Map?)?['case_class_hits'] == 0,
                          _detectionDetail(c['detection'])),
                    ],
                  ),
                ),
            if (annotated.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Annotated', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 6),
              for (final a in annotated)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(a.toString(),
                        height: 200, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            const Text('Could not load annotated image')),
                  ),
                ),
            ],
            const SizedBox(height: 8),
            Text(
              'Limit: the detector cannot prove absence — uncertain cases go to human review.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  String _detail(Map? m) {
    if (m == null) return '';
    if (m['distance_m'] != null) return '${m['distance_m']} m away';
    if (m['age_min'] != null) return 'taken ${m['age_min']} min ago';
    if (m['best_hamming'] != null && (m['best_hamming'] as num) >= 0) {
      return 'closest match distance ${m['best_hamming']}';
    }
    if (m['reason'] != null) return m['reason'].toString().replaceAll('_', ' ');
    return '';
  }

  String _detectionDetail(dynamic d) {
    if (d is! Map) return '';
    final hits = d['case_class_hits'] ?? 0;
    if ((hits as num) > 0) return '$hits litter hit${hits == 1 ? '' : 's'} remain';
    return 'no litter above threshold';
  }

  Widget _checkRow(BuildContext context, String label, bool ok, String detail) {
    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(
        children: [
          Icon(ok ? Icons.check_circle : Icons.cancel,
              size: 16, color: ok ? Colors.green : Colors.red),
          const SizedBox(width: 6),
          Expanded(child: Text(label)),
          if (detail.isNotEmpty)
            Text(detail, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
