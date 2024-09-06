# Akıllı Güvenlik Kamera Sistemi

Bu proje, gerçek zamanlı nesne tespiti ve anormallik algılama özelliklerine sahip bir akıllı güvenlik kamera sistemi uygulamasıdır.

## Özellikler

- Gerçek zamanlı video işleme
- Nesne tespiti ve sınıflandırması (insan, araç, hayvan, diğer)
- Anormallik algılama (hızlı hareket, ani görünme/kaybolma, kısıtlı alan ihlali)
- Otomatik kayıt özelliği
- Kullanıcı dostu arayüz
- E-posta bildirimleri
- Performans modu

## Kurulum

1. Bu repository'yi klonlayın:
   ```
   git clone https://github.com/aslanonkar/AGKS.git
   cd AGKS
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```
   pip install -r requirements.txt
   ```

3. Veritabanını oluşturun:
   ```
   sqlite3 security_camera.db < database_schema.sql
   ```

4. Uygulamayı çalıştırın:
   ```
   python SSCS.py
   ```
 
## Kullanım

1. Uygulama başlatıldığında, ana pencere açılacaktır.
2. "Select Video" veya "Switch to Webcam" butonlarını kullanarak video kaynağını seçin.
3. Nesne tespiti ve anormallik algılama ayarlarını yan panelden yapılandırın.
4. "Options" butonunu kullanarak e-posta bildirim ayarlarını yapın.
5. Kısıtlı alan belirlemek için "Restricted Area" seçeneğini etkinleştirin ve video üzerinde bir alan çizin.
6. Anormallikleri ve tespitleri "Detections" ve "Anomalies" sekmelerinden takip edin.
7. Kaydedilen videoları "Recorded Videos" sekmesinden izleyin.

## Proje Yapısı

- `SSCS.py`: Ana uygulama dosyası
- `requirements.txt`: Gerekli Python kütüphaneleri
- `database_schema.sql`: Veritabanı şeması ve örnek veri
- `technical_doc.md`: Teknik dokümantasyon

