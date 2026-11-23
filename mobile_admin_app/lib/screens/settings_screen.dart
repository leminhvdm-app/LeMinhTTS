import 'package:flutter/material.dart';
import '../services/firebase_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final FirebaseService _service = FirebaseService();
  final _urlCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final url = await _service.getFirebaseUrl();
    final pin = await _service.getAdminPin();
    setState(() {
      _urlCtrl.text = url;
      _pinCtrl.text = pin;
    });
  }

  Future<void> _saveSettings() async {
    setState(() => _isSaving = true);
    final url = _urlCtrl.text.trim();
    final pin = _pinCtrl.text.trim();

    if (pin.length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mã PIN tối thiểu 4 chữ số!'), backgroundColor: Colors.orange),
      );
      setState(() => _isSaving = false);
      return;
    }

    await _service.setFirebaseUrl(url);
    await _service.setAdminPin(pin);

    if (mounted) {
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã lưu cài đặt kết nối thành công!'), backgroundColor: Colors.green),
      );
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: const Text('Cài Đặt Máy Chủ Firebase'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Cấu hình Realtime Database',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Nhập URL Firebase Realtime Database của bạn để đồng bộ với app PC.',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _urlCtrl,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'Firebase Database URL',
                labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                hintText: 'https://project-id-default-rtdb.firebaseio.com',
                hintStyle: const TextStyle(color: Color(0xFF64748B)),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Bảo mật ứng dụng',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _pinCtrl,
              keyboardType: TextInputType.number,
              obscureText: true,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'Mã PIN Admin mở app',
                labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF38BDF8),
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: _isSaving ? null : _saveSettings,
                child: _isSaving
                    ? const CircularProgressIndicator(color: Colors.black)
                    : const Text('Lưu Thay Đổi', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'ℹ️ Hướng dẫn thiết lập Firebase (Miễn phí):',
                    style: TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  SizedBox(height: 8),
                  Text(
                    '1. Truy cập console.firebase.google.com và tạo Project mới.\n'
                    '2. Vào mục "Build" -> "Realtime Database" -> Bấm Create Database.\n'
                    '3. Chọn chế độ Test mode (Rules cho phép read/write: true).\n'
                    '4. Copy đường link Database (dạng https://...firebaseio.com) và dán vào ô bên trên và trong app LeMinhTTS PC.',
                    style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 12, height: 1.5),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
