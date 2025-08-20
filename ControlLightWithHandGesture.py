import cv2
import mediapipe as mp
import requests
import time
import math

# --- AYARLAR ---
ESP32_IP = "192.168.129.165"  # ESP32'NİN IP ADRESİNİ KONTROL EDİN
HEART_DISTANCE_THRESHOLD = 0.1 # Kalp işareti için eşik
BLINK_INTERVAL = 0.2       # Işığın yanıp sönme hızı (saniye cinsinden)
DEBOUNCE_TIME = 1        # Diğer komutlar için bekleme süresi
# ----------------

# MediaPipe el modelini iki eli algılayacak şekilde hazırla
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Kamera başlat
cap = cv2.VideoCapture(0)

# Durum ve zamanlama değişkenleri
last_status = None
last_change_time = 0
last_blink_time = 0
light_is_on_for_blink = False

def calculate_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def send_esp_command(command):
    try:
        url = f"http://{ESP32_IP}/{command}"
        requests.get(url, timeout=0.5)
    except requests.exceptions.RequestException:
        # Hata mesajını sürekli yazdırmamak için sessizce geçebiliriz
        pass

while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    current_status = "BILINMIYOR"

    if results.multi_hand_landmarks:
        # --- 1. KALP HAREKETİ KONTROLÜ ---
        if len(results.multi_hand_landmarks) == 2:
            hand1 = results.multi_hand_landmarks[0].landmark
            hand2 = results.multi_hand_landmarks[1].landmark

            ##### YENİ VE DOĞRU KALP MANTIĞI #####
            # Kural 1: Başparmakların uçları (ID 4) altta birleşiyor mu?
            thumb_tip_dist = calculate_distance(hand1[4], hand2[4])
            
            # Kural 2: İşaret parmaklarının uçları (ID 8) üstte birleşiyor mu?
            index_tip_dist = calculate_distance(hand1[8], hand2[8])
            
            # Kural 3: İşaret parmakları, başparmaklardan daha mı yukarıda? (Y ekseni değeri daha küçük olmalı)
            is_correct_orientation = hand1[8].y < hand1[4].y and hand2[8].y < hand2[4].y
            
            # Tüm kurallar sağlanıyorsa, bu doğal bir kalp işaretidir.
            if thumb_tip_dist < HEART_DISTANCE_THRESHOLD and index_tip_dist < (HEART_DISTANCE_THRESHOLD * 1.5) and is_correct_orientation:
                # İşaret parmakları için eşiği biraz daha esnek yapıyoruz (1.5 katı) çünkü tam değmeyebilirler.
                current_status = "KALP"
            #######################################

        # --- 2. TEK EL HAREKETLERİ KONTROLÜ (Eğer kalp değilse) ---
        if current_status != "KALP":
            hand_landmarks = results.multi_hand_landmarks[0].landmark
            
            fingers_up_count = 0
            for id in [8, 12, 16, 20]:
                if hand_landmarks[id].y < hand_landmarks[id - 2].y:
                    fingers_up_count += 1
            
            if fingers_up_count >= 3:
                current_status = "ACIK"
            elif fingers_up_count == 0:
                current_status = "KAPALI"

        for hand_lms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
    
    # --- 3. KOMUT GÖNDERME MANTIĞI ---
    if current_status == "KALP":
        if time.time() - last_blink_time > BLINK_INTERVAL:
            light_is_on_for_blink = not light_is_on_for_blink
            command = "ac" if light_is_on_for_blink else "kapat"
            send_esp_command(command)
            last_blink_time = time.time()
        last_status = "KALP"
    
    else:
        if last_status == "KALP":
            send_esp_command("kapat")
            light_is_on_for_blink = False
        
        if current_status != last_status and (time.time() - last_change_time > DEBOUNCE_TIME):
            if current_status == "ACIK":
                print("Komut gönderiliyor: IŞIK AÇ (El Açık)")
                send_esp_command("ac")
                last_status = current_status
                last_change_time = time.time()
            elif current_status == "KAPALI":
                print("Komut gönderiliyor: IŞIK KAPAT (Yumruk)")
                send_esp_command("kapat")
                last_status = current_status
                last_change_time = time.time()

    cv2.putText(img, f"Durum: {current_status}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (0, 255, 255), 3)
    cv2.imshow("El Hareketi ile Lamba Kontrolü", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- 4. GÜVENLİ ÇIKIŞ ---
print("Program sonlandırılıyor, ışık kapatılıyor...")
send_esp_command("kapat")

cap.release()
cv2.destroyAllWindows()