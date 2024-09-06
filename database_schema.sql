-- Detections tablosu
CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    object_type TEXT,
    confidence REAL,
    x_min INTEGER,
    y_min INTEGER,
    x_max INTEGER,
    y_max INTEGER,
    frame_number INTEGER
);

-- Anomalies tablosu
CREATE TABLE anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    anomaly_type TEXT,
    description TEXT,
    x_min INTEGER,
    y_min INTEGER,
    x_max INTEGER,
    y_max INTEGER,
    frame_number INTEGER,
    severity INTEGER
);

-- Örnek veri ekleme
INSERT INTO detections (timestamp, object_type, confidence, x_min, y_min, x_max, y_max, frame_number)
VALUES ('2024-09-06 14:30:00', 'person', 0.95, 100, 150, 300, 400, 1234);

INSERT INTO anomalies (timestamp, anomaly_type, description, x_min, y_min, x_max, y_max, frame_number, severity)
VALUES ('2024-09-06 14:30:05', 'Rapid Movement', 'Hýzlý hareket tespit edildi', 200, 250, 350, 450, 1240, 2);