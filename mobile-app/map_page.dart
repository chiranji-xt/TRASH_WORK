import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'report_store.dart';
import 'report_details_page.dart';
import 'all_reports_page.dart';
import 'report_page.dart';

class MapPage extends StatefulWidget {
  const MapPage({super.key});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  GoogleMapController? _mapController;
  Position? _currentPosition;
  Set<Marker> _markers = {};
  String _filterCategory = 'All';
  LatLng? _pinnedLocation;
  bool _pinningMode = false;

  @override
  void initState() {
    super.initState();
    _getCurrentLocation();
    _loadMarkers();
    reportStore.addListener(_loadMarkers);
    // Fetch reports on load to ensure persistence
    reportStore.fetchReports();
  }

  @override
  void dispose() {
    reportStore.removeListener(_loadMarkers);
    _mapController?.dispose();
    super.dispose();
  }

  Future<void> _getCurrentLocation() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return;

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever) return;

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() {
        _currentPosition = position;
      });

      // Move camera to current location
      if (_mapController != null && _currentPosition != null) {
        _mapController!.animateCamera(
          CameraUpdate.newLatLngZoom(
            LatLng(_currentPosition!.latitude, _currentPosition!.longitude),
            15.0,
          ),
        );
      }
    } catch (e) {
      debugPrint('Error getting location: $e');
    }
  }

  void _loadMarkers() {
    final items = reportStore.value;
    final markers = <Marker>{};

    for (final item in items) {
      // Filter logic
      if (_filterCategory != 'All' && item.category != _filterCategory) {
        continue;
      }

      if (item.latitude != null && item.longitude != null) {
        final markerId = MarkerId(item.id);
        markers.add(
          Marker(
            markerId: markerId,
            position: LatLng(item.latitude!, item.longitude!),
            infoWindow: InfoWindow(
              title: item.title,
              snippet: '${item.category} • Severity: ${item.severity}',
            ),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ReportDetailsPage(item: item),
                ),
              );
            },
          ),
        );
      }
    }

    // Add pinned location marker if in pinning mode
    if (_pinnedLocation != null) {
      markers.add(
        Marker(
          markerId: const MarkerId('pinned_location'),
          position: _pinnedLocation!,
          icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed),
          infoWindow: const InfoWindow(
            title: 'Pinned Location',
            snippet: 'Tap to report at this location',
          ),
          onTap: () {
            // Navigate to report page with pre-filled location
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const ReportPage(),
              ),
            );
          },
        ),
      );
    }

    setState(() {
      _markers = markers;
    });
  }

  void _onMapTap(LatLng position) {
    if (_pinningMode) {
      setState(() {
        _pinnedLocation = position;
      });
      _loadMarkers();
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Location pinned: ${position.latitude.toStringAsFixed(6)}, ${position.longitude.toStringAsFixed(6)}'),
          action: SnackBarAction(
            label: 'Report here',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const ReportPage(),
                ),
              );
            },
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      body: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: CameraPosition(
              target: _currentPosition != null
                  ? LatLng(_currentPosition!.latitude, _currentPosition!.longitude)
                  : const LatLng(20.5937, 78.9629), // Default to India
              zoom: 12.0,
            ),
            onMapCreated: (controller) {
              _mapController = controller;
              if (_currentPosition != null) {
                controller.animateCamera(
                  CameraUpdate.newLatLngZoom(
                    LatLng(_currentPosition!.latitude, _currentPosition!.longitude),
                    15.0,
                  ),
                );
              }
            },
            markers: _markers,
            myLocationEnabled: true,
            myLocationButtonEnabled: false,
            mapType: MapType.normal,
            onTap: _onMapTap,
          ),
          
          // Top Gradient Header
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    theme.colorScheme.primary,
                    theme.colorScheme.secondary,
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(24),
                  bottomRight: Radius.circular(24),
                ),
              ),
              padding: const EdgeInsets.fromLTRB(16, 48, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Explore Garbage Reports',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      color: theme.colorScheme.onPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: DropdownButton<String>(
                            value: _filterCategory,
                            dropdownColor: theme.colorScheme.surface,
                            underline: const SizedBox(),
                            isExpanded: true,
                            style: TextStyle(color: theme.colorScheme.onPrimary),
                            items: const [
                              DropdownMenuItem(value: 'All', child: Text('All Categories')),
                              DropdownMenuItem(value: 'Waste', child: Text('Waste')),
                              DropdownMenuItem(value: 'Plastic', child: Text('Plastic')),
                              DropdownMenuItem(value: 'General', child: Text('General')),
                            ],
                            onChanged: (v) {
                              setState(() => _filterCategory = v ?? 'All');
                              _loadMarkers();
                            },
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        icon: Icon(
                          _pinningMode ? Icons.location_on : Icons.location_off,
                          color: theme.colorScheme.onPrimary,
                        ),
                        onPressed: () {
                          setState(() {
                            _pinningMode = !_pinningMode;
                            if (!_pinningMode) {
                              _pinnedLocation = null;
                              _loadMarkers();
                            }
                          });
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(_pinningMode 
                                  ? 'Tap on map to pin a location' 
                                  : 'Pinning mode disabled'),
                              duration: const Duration(seconds: 2),
                            ),
                          );
                        },
                        tooltip: _pinningMode ? 'Disable pinning' : 'Enable pinning',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Floating Action Buttons
          Positioned(
            bottom: 80,
            right: 16,
            child: Column(
              children: [
                FloatingActionButton(
                  heroTag: 'refresh_pins',
                  mini: true,
                  onPressed: () {
                    reportStore.fetchReports();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Refreshing map pins...'),
                        duration: Duration(seconds: 1),
                      ),
                    );
                  },
                  tooltip: 'Show All Pins',
                  child: const Icon(Icons.refresh),
                ),
                const SizedBox(height: 8),
                FloatingActionButton(
                  heroTag: 'zoom_in',
                  mini: true,
                  onPressed: () {
                    _mapController?.animateCamera(CameraUpdate.zoomIn());
                  },
                  child: const Icon(Icons.add),
                ),
                const SizedBox(height: 8),
                FloatingActionButton(
                  heroTag: 'zoom_out',
                  mini: true,
                  onPressed: () {
                    _mapController?.animateCamera(CameraUpdate.zoomOut());
                  },
                  child: const Icon(Icons.remove),
                ),
                const SizedBox(height: 8),
                FloatingActionButton(
                  heroTag: 'my_location',
                  mini: true,
                  onPressed: () {
                    if (_currentPosition != null) {
                      _mapController?.animateCamera(
                        CameraUpdate.newLatLngZoom(
                          LatLng(_currentPosition!.latitude, _currentPosition!.longitude),
                          15.0,
                        ),
                      );
                    } else {
                      _getCurrentLocation();
                    }
                  },
                  child: const Icon(Icons.my_location),
                ),
              ],
            ),
          ),

          // Bottom Info Card
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Card(
                  elevation: 4,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          color: theme.colorScheme.primary,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                _pinningMode 
                                    ? 'Tap on map to pin location'
                                    : '${_markers.length} reports on map',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              if (_currentPosition != null)
                                Text(
                                  'Your location: ${_currentPosition!.latitude.toStringAsFixed(4)}, ${_currentPosition!.longitude.toStringAsFixed(4)}',
                                  style: theme.textTheme.bodySmall,
                                ),
                            ],
                          ),
                        ),
                        TextButton(
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => const AllReportsPage(),
                              ),
                            );
                          },
                          child: const Text('View All'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
