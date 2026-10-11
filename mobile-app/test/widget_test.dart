import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_app/report_store.dart';

void main() {
  test('ReportItem parses backend /predict JSON', () {
    final item = ReportItem.fromJson(const {
      'id': 7,
      'prediction': 'Metal Waste',
      'confidence': 0.8836,
      'severity': 3,
      'status': 'pending',
      'latitude': 18.5204,
      'longitude': 73.8567,
      'image_path': '/uploads/a.jpg',
      'boxed_image_path': '/annotated/b.jpg',
      'case_id': 12,
      'detections': {
        'count': 2,
        'severity': 3,
        'primary': {'class': 'Metal Waste', 'confidence': 0.8836},
        'items': [
          {'class': 'Metal Waste', 'confidence': 0.8836},
          {'class': 'Plastic Waste', 'confidence': 0.71},
        ],
      },
    });

    expect(item.id, '7');
    expect(item.prediction, 'Metal Waste');
    expect(item.confidence, 0.8836);
    expect(item.boxedImageUrl, contains('/annotated/b.jpg'));
    expect(item.caseId, 12);
    expect(item.detections.length, 2);
    expect(item.detections[0].className, 'Metal Waste');
    expect(item.detections[1].confidence, 0.71);
  });
}
