import 'package:flutter/material.dart';

class FittingPainter extends CustomPainter {
  FittingPainter(this.garment, this.scale, this.offset);
  final Map<String, dynamic>? garment;
  final double scale;
  final double offset;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.translate(size.width / 2, 0);
    final body = Paint()..color = const Color(0xffb7bfca);
    canvas.drawCircle(const Offset(0, 40), 28, body);
    canvas.drawRRect(
        RRect.fromRectAndRadius(
            const Rect.fromLTWH(-40, 75, 80, 155), const Radius.circular(20)),
        body);
    canvas.drawRect(const Rect.fromLTWH(-38, 210, 30, 175), body);
    canvas.drawRect(const Rect.fromLTWH(8, 210, 30, 175), body);
    canvas.drawRect(const Rect.fromLTWH(-65, 90, 25, 145), body);
    canvas.drawRect(const Rect.fromLTWH(40, 90, 25, 145), body);
    if (garment == null) return;
    final colors = {
      'azul': Colors.blue.shade800,
      'negro': Colors.black87,
      'blanco': Colors.white,
      'gris': Colors.grey,
      'verde': Colors.green.shade700,
      'rojo': Colors.red
    };
    final paint = Paint()
      ..color = colors['${garment!['color']}'.toLowerCase()] ?? Colors.purple;
    final pants = garment!['garment'] == 'pants';
    canvas.translate(0, (pants ? 205 : 80) + offset);
    canvas.scale(scale);
    final path = Path();
    if (pants) {
      path.moveTo(-42, 0);
      path.lineTo(42, 0);
      path.lineTo(48, 180);
      path.lineTo(10, 180);
      path.lineTo(0, 55);
      path.lineTo(-10, 180);
      path.lineTo(-48, 180);
    } else {
      path.moveTo(-35, 0);
      path.lineTo(-15, -8);
      path.quadraticBezierTo(0, 12, 15, -8);
      path.lineTo(35, 0);
      path.lineTo(80, 38);
      path.lineTo(58, 64);
      path.lineTo(40, 45);
      path.lineTo(40, 145);
      path.lineTo(-40, 145);
      path.lineTo(-40, 45);
      path.lineTo(-58, 64);
      path.lineTo(-80, 38);
    }
    path.close();
    canvas.drawPath(path, paint);
    canvas.drawPath(
        path,
        Paint()
          ..color = Colors.black54
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2);
  }

  @override
  bool shouldRepaint(covariant FittingPainter oldDelegate) =>
      oldDelegate.garment != garment ||
      oldDelegate.scale != scale ||
      oldDelegate.offset != offset;
}
