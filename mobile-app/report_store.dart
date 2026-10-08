import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as path;
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'config.dart';

class ReportItem {
	final String id;
	final String title;
	final String description;
	final String category;
	final int severity;
	final bool includeLocation;
	final File? imageFile;
	final String? imageUrl;
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
		this.latitude,
		this.longitude,
		this.status = 'Pending',
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
		latitude: latitude ?? this.latitude,
		longitude: longitude ?? this.longitude,
		status: status ?? this.status,
		createdAt: createdAt,
	);
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
			final response = await http.get(Uri.parse('$baseUrl/reports'));
			if (response.statusCode == 200) {
				final List<dynamic> reportsJson = json.decode(response.body);
				
				final List<ReportItem> newItems = reportsJson.map((json) {
					return ReportItem(
						id: json['id']?.toString() ?? '',
						title: 'Report ${json['id'].toString().substring(0, 6)}',
						description: (json['labels'] as List?)?.join(', ') ?? 'Detected Waste',
						category: 'Waste',
						severity: 3,
						includeLocation: json['latitude'] != null,
						latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
						longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
						imageUrl: json['image_path'] != null ? '$baseUrl/uploads/${path.basename(json['image_path'])}' : null,
						status: json['status'] ?? 'Pending',
						createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
					);
				}).toList();
				
				// Merge with local items if needed, or just replace
				// For now, let's prepend fetched items to existing ones, or just replace
				// Replacing is safer to avoid duplicates if we don't have local persistence logic yet
				value = newItems; 
				notifyListeners();
			}
		} catch (e) {
			debugPrint('Error fetching reports: $e');
		}
	}
}

final ReportStore reportStore = ReportStore();
