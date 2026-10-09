// Backend URL configuration.
//
// Set via --dart-define at build/run time (never commit ngrok URLs):
//   flutter run --dart-define=API_BASE_URL=https://<your-subdomain>.ngrok-free.dev
//   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000   (Android emulator -> host localhost)
//   flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000 (physical device via LAN IP)
//
// Defaults to the Android-emulator loopback for local development.
const String baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
