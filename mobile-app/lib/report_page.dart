import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import 'detection_preview_page.dart';
import 'report_store.dart';

/// Report form tab. Picks a photo, collects metadata, and uploads to the
/// real backend (POST /predict). Previously missing, which broke compilation.
class ReportPage extends StatefulWidget {
  const ReportPage({super.key});

  @override
  State<ReportPage> createState() => _ReportPageState();
}

class _ReportPageState extends State<ReportPage> {
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _latCtrl = TextEditingController();
  final _lonCtrl = TextEditingController();
  String _category = 'General';
  int _severity = 3;
  XFile? _image;
  bool _submitting = false;
  String? _result;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    _latCtrl.dispose();
    _lonCtrl.dispose();
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    final picker = ImagePicker();
    final file = await picker.pickImage(source: source, maxWidth: 1600);
    if (file != null) setState(() => _image = file);
  }

  Future<void> _useCurrentLocation() async {
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Location permission denied')),
          );
        }
        return;
      }
      final pos = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
      setState(() {
        _latCtrl.text = pos.latitude.toStringAsFixed(6);
        _lonCtrl.text = pos.longitude.toStringAsFixed(6);
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Location error: $e')));
      }
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_image == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a photo first')),
      );
      return;
    }
    final lat = double.tryParse(_latCtrl.text.trim());
    final lon = double.tryParse(_lonCtrl.text.trim());
    if (lat == null || lon == null || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter valid latitude (-90..90) and longitude (-180..180)')),
      );
      return;
    }

    setState(() {
      _submitting = true;
      _result = null;
    });
    try {
      // Preview first: run detection, show boxed image + class.
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => DetectionPreviewPage(
          imageFile: File(_image!.path),
          latitude: lat,
          longitude: lon,
          category: _category,
          severity: _severity,
          title: _titleCtrl.text.trim(),
          description: _descCtrl.text.trim(),
        ),
      ));
      // Refresh history after returning from preview (upload happens there).
      await reportStore.fetchReports();
      setState(() => _result = 'Done — see History for the new report.');
    } catch (e) {
      setState(() => _result = 'Upload failed: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Upload failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Photo picker
            GestureDetector(
              onTap: () => _pick(ImageSource.gallery),
              child: Container(
                height: 180,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                ),
                clipBehavior: Clip.antiAlias,
                child: _image == null
                    ? const Center(child: Text('Tap to pick a photo'))
                    : Image.file(File(_image!.path), fit: BoxFit.cover),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                TextButton.icon(
                  onPressed: () => _pick(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Camera'),
                ),
                TextButton.icon(
                  onPressed: () => _pick(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Gallery'),
                ),
              ],
            ),
            TextFormField(
              controller: _titleCtrl,
              decoration: const InputDecoration(labelText: 'Title'),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _descCtrl,
              decoration: const InputDecoration(labelText: 'Description'),
              maxLines: 3,
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _category,
              decoration: const InputDecoration(labelText: 'Category'),
              items: const ['General', 'Road', 'Sanitation', 'Safety', 'Waste', 'Water', 'Electricity', 'Environment']
                  .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                  .toList(),
              onChanged: (v) => setState(() => _category = v ?? 'General'),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Text('Severity'),
                Expanded(
                  child: Slider(
                    min: 1,
                    max: 5,
                    divisions: 4,
                    value: _severity.toDouble(),
                    label: _severity.toString(),
                    onChanged: (v) => setState(() => _severity = v.round()),
                  ),
                ),
                Text('$_severity'),
              ],
            ),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _latCtrl,
                    decoration: const InputDecoration(labelText: 'Latitude'),
                    keyboardType: TextInputType.number,
                    validator: (v) => (v == null || double.tryParse(v.trim()) == null) ? 'Required' : null,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextFormField(
                    controller: _lonCtrl,
                    decoration: const InputDecoration(labelText: 'Longitude'),
                    keyboardType: TextInputType.number,
                    validator: (v) => (v == null || double.tryParse(v.trim()) == null) ? 'Required' : null,
                  ),
                ),
                IconButton(
                  onPressed: _useCurrentLocation,
                  icon: const Icon(Icons.my_location),
                  tooltip: 'Use current location',
                ),
              ],
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
              label: Text(_submitting ? 'Uploading…' : 'Submit report'),
            ),
            if (_result != null) ...[
              const SizedBox(height: 8),
              Text(_result!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}
