## Kurulum

1. Python 3.8 veya üstü bir sürüm yüklü olduğundan emin olun.

2. Proje dizininde bir sanal ortam oluşturun ve etkinleştirin:
   ```
   python -m venv venv
   source venv/bin/activate  # Linux veya macOS için
   venv\Scripts\activate  # Windows için
   ```

3. Gerekli paketleri yükleyin:
   ```
   pip install -r requirements.txt
   ```

4. YOLOv5 modelini indirin:
   ```
   python -c "from ultralytics import YOLO; YOLO('yolov5s.pt')"
   ```

5. Uygulamayı çalıştırın:
   ```
   python CurrentVersion.py
   ```