# Ak�ll� G�venlik Kamera Sistemi - Teknik Dok�mantasyon

## Kullan�lan Teknolojiler

1. **Python**: Ana programlama dili
2. **OpenCV (cv2)**: Video i�leme ve g�r�nt� analizi i�in
3. **PyTorch**: Derin ��renme modeli (YOLOv5) i�in
4. **CustomTkinter**: Kullan�c� aray�z� i�in
5. **SQLite**: Veritaban� y�netimi i�in

## Mimari Kararlar

1. **Mod�ler Yap�**: Uygulama, farkl� i�levleri y�neten s�n�flar (�rn. DatabaseManager) kullan�larak mod�ler bir �ekilde tasarlanm��t�r. 

2. **Ger�ek Zamanl� ��leme**: Video ak���, performans� art�rmak i�in ayr� bir thread'de i�lenir.

3. **Nesne Tespiti**: YOLOv5 modeli, h�zl� ve do�ru nesne tespiti i�in kullan�lm��t�r. Model, �nceden e�itilmi� a��rl�klarla y�klenir ve gerekti�inde fine-tune edilebilir.

4. **Anomali Alg�lama**: �zelle�tirilmi� algoritmalar� kullanarak h�zl� hareket, ani g�r�nme/kaybolma ve k�s�tl� alan ihlali gibi anomalileri tespit eder.

5. **Veritaban� Entegrasyonu**: Tespit edilen nesnelerin ve anomalilerin kayd�, ge�mi� verilerin analizi ve raporlama i�in SQLite. 

6. **Kullan�c� Aray�z�**: CustomTkinter, modern ve kullan�c� dostu bir aray�z sa�lar. Aray�z, canl� video ak���, alg�lama sonu�lar� ve ayarlar i�in farkl� b�l�mler i�erir.

7. **Performans Optimizasyonu**: Y�ksek FPS sa�lamak i�in bir performans modu eklenmi�tir. Bu mod, i�leme h�z�n� art�rmak i�in baz� kareleri atlar.

8. **Otomasyon ve Bildirimler**: Sistem, belirli olaylar (�rn. anomaliler) tespit edildi�inde otomatik olarak kay�t yapabilir ve e-posta bildirimleri g�nderebilir.

## Gelecek �yile�tirmeler

1. �oklu kamera deste�i
2. Geli�mi� anomali alg�lama algoritmalar�
3. Bulut entegrasyonu ve uzaktan eri�im
4. Geli�mi� raporlama ve analiz ara�lar�
5. Responsive tasar�m.