import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key, required this.onFinish});

  final VoidCallback onFinish;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final PageController _controller = PageController();
  int _index = 0;

  final List<_OnboardData> _pages = const [
    _OnboardData(
      title: 'Welcome to SmartCity',
      subtitle: 'Empowering you to build a cleaner, greener future.',
      icon: Icons.eco,
      color: Color(0xFF6C63FF),
    ),
    _OnboardData(
      title: 'Snap & Report',
      subtitle: 'Instantly report waste and hazards with just a photo.',
      icon: Icons.camera_enhance_rounded,
      color: Color(0xFF00BFA6),
    ),
    _OnboardData(
      title: 'Make an Impact',
      subtitle: 'Track your contributions and help your city thrive.',
      icon: Icons.public,
      color: Color(0xFFFF6584),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Animated Background
          Positioned.fill(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 500),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    _pages[_index].color.withOpacity(0.1),
                    Colors.white,
                    _pages[_index].color.withOpacity(0.05),
                  ],
                ),
              ),
            ),
          ),
          
          SafeArea(
            child: Column(
              children: [
                Expanded(
                  child: PageView.builder(
                    controller: _controller,
                    itemCount: _pages.length,
                    onPageChanged: (i) => setState(() => _index = i),
                    itemBuilder: (_, i) => _OnboardSlide(data: _pages[i], isActive: _index == i),
                  ),
                ),
                
                // Bottom Controls
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      // Indicators
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(_pages.length, (i) {
                          final bool active = i == _index;
                          return AnimatedContainer(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeOutBack,
                            margin: const EdgeInsets.symmetric(horizontal: 4),
                            height: 8,
                            width: active ? 32 : 8,
                            decoration: BoxDecoration(
                              color: active ? _pages[_index].color : Colors.grey.shade300,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          );
                        }),
                      ),
                      const SizedBox(height: 32),
                      
                      // Action Button
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: FilledButton(
                          onPressed: () {
                            if (_index == _pages.length - 1) {
                              widget.onFinish();
                            } else {
                              _controller.nextPage(
                                duration: const Duration(milliseconds: 500),
                                curve: Curves.easeInOutCubic,
                              );
                            }
                          },
                          style: FilledButton.styleFrom(
                            backgroundColor: _pages[_index].color,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                            elevation: 4,
                            shadowColor: _pages[_index].color.withOpacity(0.4),
                          ),
                          child: Text(
                            _index == _pages.length - 1 ? 'Get Started' : 'Next',
                            style: GoogleFonts.poppins(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ).animate(target: _index == _pages.length - 1 ? 1 : 0)
                        .shimmer(duration: 1200.ms, color: Colors.white38),
                      ),
                      const SizedBox(height: 16),
                      
                      // Skip Button
                      if (_index != _pages.length - 1)
                        TextButton(
                          onPressed: widget.onFinish,
                          child: Text(
                            'Skip',
                            style: GoogleFonts.poppins(
                              color: Colors.grey.shade600,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ).animate().fadeIn(),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OnboardData {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  const _OnboardData({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
  });
}

class _OnboardSlide extends StatelessWidget {
  const _OnboardSlide({required this.data, required this.isActive});
  final _OnboardData data;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Icon Circle
          Container(
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: data.color.withOpacity(0.1),
            ),
            child: Icon(data.icon, size: 80, color: data.color)
                .animate(target: isActive ? 1 : 0)
                .scale(duration: 600.ms, curve: Curves.easeOutBack)
                .rotate(duration: 600.ms, curve: Curves.easeOutBack, begin: -0.1, end: 0),
          ).animate().fadeIn(duration: 600.ms).slideY(begin: 0.2, end: 0),
          
          const SizedBox(height: 48),
          
          // Title
          Text(
            data.title,
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
              height: 1.2,
            ),
          ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.2, end: 0),
          
          const SizedBox(height: 16),
          
          // Subtitle
          Text(
            data.subtitle,
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
              fontSize: 16,
              color: Colors.black54,
              height: 1.5,
            ),
          ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.2, end: 0),
        ],
      ),
    );
  }
}
