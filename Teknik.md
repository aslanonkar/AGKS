# Akýllý Güvenlik Kamera Sistemi - Teknik Dokümantasyon

## Kullanýlan Teknolojiler

1. **Python**: Ana programlama dili
2. **OpenCV (cv2)**: Video iþleme ve görüntü analizi için
3. **PyTorch**: Derin öðrenme modeli (YOLOv5) için
4. **CustomTkinter**: Kullanýcý arayüzü için
5. **SQLite**: Veritabaný yönetimi için

## Mimari Kararlar

1. **Modüler Yapý**: Uygulama, farklý iþlevleri yöneten sýnýflar (örn. DatabaseManager) kullanýlarak modüler bir þekilde tasarlanmýþtýr. 

2. **Gerçek Zamanlý Ýþleme**: Video akýþý, performansý artýrmak için ayrý bir thread'de iþlenir.

3. **Nesne Tespiti**: YOLOv5 modeli, hýzlý ve doðru nesne tespiti için kullanýlmýþtýr. Model, önceden eðitilmiþ aðýrlýklarla yüklenir ve gerektiðinde fine-tune edilebilir.

4. **Anomali Algýlama**: Özelleþtirilmiþ algoritmalarý kullanarak hýzlý hareket, ani görünme/kaybolma ve kýsýtlý alan ihlali gibi anomalileri tespit eder.

5. **Veritabaný Entegrasyonu**: Tespit edilen nesnelerin ve anomalilerin kaydý, geçmiþ verilerin analizi ve raporlama için SQLite. 

6. **Kullanýcý Arayüzü**: CustomTkinter, modern ve kullanýcý dostu bir arayüz saðlar. Arayüz, canlý video akýþý, algýlama sonuçlarý ve ayarlar için farklý bölümler içerir.

7. **Performans Optimizasyonu**: Yüksek FPS saðlamak için bir performans modu eklenmiþtir. Bu mod, iþleme hýzýný artýrmak için bazý kareleri atlar.

8. **Otomasyon ve Bildirimler**: Sistem, belirli olaylar (örn. anomaliler) tespit edildiðinde otomatik olarak kayýt yapabilir ve e-posta bildirimleri gönderebilir.

## Gelecek Ýyileþtirmeler

1. Çoklu kamera desteði
2. Geliþmiþ anomali algýlama algoritmalarý
3. Bulut entegrasyonu ve uzaktan eriþim
4. Geliþmiþ raporlama ve analiz araçlarý
5. Responsive tasarým.