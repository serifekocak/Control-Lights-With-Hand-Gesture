import cv2
import mediapipe as mp
import requests
import time

# --- AYARLAR ---
ESP32_IP = "192.168.159.165"  # ESP32'NİN IP ADRESİNİ BURAYA GİRİN
# ----------------

# MediaPipe el modelini hazırla
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# Parmak uçlarının ID'leri
tip_ids = [4, 8, 12, 16, 20]

# Kamera başlat
cap = cv2.VideoCapture(0)

# Elin son durumunu tutmak için değişken (Gereksiz istek göndermemek için)
last_status = None
debounce_time = 1  # Durum değişikliği sonrası bekleme süresi (saniye)
last_change_time = 0

def send_command(status):
    """ESP32'ye komut gönderir."""
    global last_status, last_change_time
    # Sadece durum değiştiyse ve bekleme süresi geçtiyse komut gönder
    if status != last_status and (time.time() - last_change_time > debounce_time):
        try:
            if status == "ACIK":
                url = f"http://{ESP32_IP}/ac"
                print("Komut gönderiliyor: IŞIK AÇ")
                requests.get(url, timeout=1)
            elif status == "KAPALI":
                url = f"http://{ESP32_IP}/kapat"
                print("Komut gönderiliyor: IŞIK KAPAT")
                requests.get(url, timeout=1)
            
            last_status = status
            last_change_time = time.time()
        except requests.exceptions.RequestException as e:
            print(f"Hata: ESP32'ye ulaşılamadı. {e}")

while True:
    success, img = cap.read()
    if not success:
        break

    # Görüntüyü çevir (ayna efekti) ve BGR'dan RGB'ye dönüştür
    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Eli işle
    results = hands.process(img_rgb)

    hand_status = "BILINMIYOR"

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Eklemleri çiz
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            landmarks = hand_landmarks.landmark
            fingers_up = []

            # 1. Baş parmak (sağ/sol ele göre x ekseninde kontrol)
            # Baş parmağın ucu, bir önceki eklemin sağındaysa (sağ el için) parmak açıktır.
            if landmarks[tip_ids[0]].x < landmarks[tip_ids[0] - 1].x:
                 fingers_up.append(1)
            else:
                 fingers_up.append(0)

            # 2. Diğer dört parmak (y ekseninde kontrol)
            for id in range(1, 5):
                # Parmağın ucu, bir altındaki eklemden daha yukarıdaysa parmak açıktır.
                if landmarks[tip_ids[id]].y < landmarks[tip_ids[id] - 2].y:
                    fingers_up.append(1)
                else:
                    fingers_up.append(0)
            
            total_fingers = fingers_up.count(1)
            
            # 4 veya 5 parmak açıksa "EL AÇIK"
            if total_fingers >= 4:
                hand_status = "ACIK"
            # 0 veya 1 parmak açıksa "EL KAPALI" (yumruk)
            elif total_fingers <= 1:
                hand_status = "KAPALI"
            
            send_command(hand_status)

            cv2.putText(img, f"Durum: {hand_status}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

    # Görüntüyü göster
    cv2.imshow("El Hareketi Algilama", img)

    # 'q' tuşuna basınca çık
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()