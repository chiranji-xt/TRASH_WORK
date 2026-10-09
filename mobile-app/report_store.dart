import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'config.dart';

/// Canonical statuses shared with the backend and dashboard: pending | cleaned.
const String kStatusPending = 'pending';
const String kStatusCleaned = 'cleaned';

String normalizeStatus(String? raw) {
  final s = (raw ?? '').toLowerCase().trim();
  if (s == 'cleaned' || s == 'resolved' || s == 'done') return kStatusCleaned;
  return kStatusPending;
}

class ReportItem {
	final String id;
	final String title;
	final String description;
	final String category;
	final int severity;
	final bool includeLocation;
	final File? imageFile;
	final String? imageUrl;
	final String? boxedImageUrl;
	final String? prediction;
	final double? confidence;
	final double? latitude;
	final double? longitude;
	final String status;
	final DateTime createdAt;

	ReportItem({
		required this.id,
		required this.title,
		required this.description,
		required this.category,
		required this.severity,
		required this.includeLocation,
		this.imageFile,
		this.imageUrl,
		this.boxedImageUrl,
		this.prediction,
		this.confidence,
		this.latitude,
		this.longitude,
		this.status = kStatusPending,
		DateTime? createdAt,
	}) : createdAt = createdAt ?? DateTime.now();

	ReportItem copyWith({
		String? title,
		String? description,
		String? category,
		int? severity,
		bool? includeLocation,
		File? imageFile,
		String? imageUrl,
		String? boxedImageUrl,
		String? prediction,
		double? confidence,
		double? latitude,
		double? longitude,
		String? status,
	}) => ReportItem(
		id: id,
		title: title ?? this.title,
		description: description ?? this.description,
		category: category ?? this.category,
		severity: severity ?? this.severity,
		includeLocation: includeLocation ?? this.includeLocation,
		imageFile: imageFile ?? this.imageFile,
		imageUrl: imageUrl ?? this.imageUrl,
		boxedImageUrl: boxedImageUrl ?? this.boxedImageUrl,
		prediction: prediction ?? this.prediction,
		confidence: confidence ?? this.confidence,
		latitude: latitude ?? this.latitude,
		longitude: longitude ?? this.longitude,
		status: status ?? this.status,
		createdAt: createdAt,
	);

  factory ReportItem.fromJson(Map<String, dynamic> json) {
    String resolveUrl(String? path) {
      if (path == null || path.isEmpty) return '';
      if (path.startsWith('http')) return path;
      return '$baseUrl${path.startsWith('/') ? path : '/$path'}';
    }
    final lat = json['latitude'] ?? json['lat'];
    final lon = json['longitude'] ?? json['lon'];
    final dets = json['detections'];
    return ReportItem(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Report ${json['id']}',
      description: json['description']?.toString() ??
          ((dets is Map ? dets['primary']?['class'] : null)?.toString() ??
              json['prediction']?.toString() ??
              'Detected Waste'),
      category: json['category']?.toString() ??
          json['prediction']?.toString() ??
          'Waste',
      severity: (json['severity'] as num?)?.toInt() ??
          ((dets is Map ? dets['severity'] : null) as num?)?.toInt() ??
          3,
      includeLocation: lat != null && lon != null,
      latitude: lat != null ? (lat as num).toDouble() : null,
      longitude: lon != null ? (lon as num).toDouble() : null,
      imageUrl: json['image_path'] != null ? resolveUrl(json['image_path'].toString()) : null,
      boxedImageUrl: json['boxed_image_path'] != null
          ? resolveUrl(json['boxed_image_path'].toString())
          : null,
      prediction: json['prediction']?.toString(),
      confidence: json['confidence'] != null ? (json['confidence'] as num).toDouble() : null,
      status: normalizeStatus(json['status']?.toString()),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }
}

/// Upload an image + metadata to POST /predict (shared with /upload-report).
/// Returns the raw decoded JSON response.
Future<Map<String, dynamic>> uploadReport({
  required File image,
  required double latitude,
  required double longitude,
  String? category,
  int? severity,
  String? title,
  String? description,
}) async {
  final uri = Uri.parse('$baseUrl/predict');
  final req = http.MultipartRequest('POST', uri)
    ..fields['latitude'] = latitude.toString()
    ..fields['longitude'] = longitude.toString();
  if (category != null) req.fields['category'] = category;
  if (severity != null) req.fields['severity'] = severity.toString();
  if (title != null) req.fields['title'] = title;
  if (description != null) req.fields['description'] = description;
  req.files.add(await http.MultipartFile.fromPath('file', image.path));
  req.headers['ngrok-skip-browser-warning'] = 'true';

  final streamed = await req.send().timeout(const Duration(seconds: 60));
  final body = await streamed.stream.bytesToString();
  if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
    throw HttpException('Upload failed (${streamed.statusCode}): $body');
  }
  return json.decode(body) as Map<String, dynamic>;
}

class ReportStore extends ValueNotifier<List<ReportItem>> {
	ReportStore() : super(const []);

	void add(ReportItem item) {
		value = [item, ...value];
		notifyListeners();
	}

	void remove(String id) {
		value = value.where((e) => e.id != id).toList(growable: false);
		notifyListeners();
	}

	void update(ReportItem item) {
		value = value.map((e) => e.id == item.id ? item : e).toList(growable: false);
		notifyListeners();
	}

	Future<void> fetchReports() async {
		try {
			final response = await http.get(
        Uri.parse('$baseUrl/reports'),
        headers: {'ngrok-skip-browser-warning': 'true'},
      ).timeout(const Duration(seconds: 30));
			if (response.statusCode == 200) {
				final List<dynamic> reportsJson = json.decode(response.body);
				value = reportsJson
            .whereType<Map<String, dynamic>>()
            .map(ReportItem.fromJson)
            .toList();
				notifyListeners();
			}
		} catch (e) {
			debugPrint('Error fetching reports: $e');
		}
	}

  Future<void> fetchReportsByStatus(String status) async {
    try {
      final s = normalizeStatus(status);
      final response = await http.get(
        Uri.parse('$baseUrl/reports/by-status/$s'),
        headers: {'ngrok-skip-browser-warning': 'true'},
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        final decoded = json.decode(response.body);
        final List<dynamic> list = decoded is List ? decoded : (decoded['reports'] as List? ?? []);
        value = list.whereType<Map<String, dynamic>>().map(ReportItem.fromJson).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error fetching reports by status: $e');
    }
  }
}

final ReportStore reportStore = ReportStore();
