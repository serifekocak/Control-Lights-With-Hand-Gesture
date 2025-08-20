#include <WiFi.h>

// --- KENDİ BİLGİLERİNİZİ GİRİN ---
const char* ssid = "Kbb-WiLokal";
const char* password = "KbbW1Lokal*";
// ---------------------------------

WiFiServer server(80); // 80 portundan bir sunucu oluştur

#define RELAY_PIN 23 // Rölenin bağlı olduğu pin

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Başlangıçta ışık kapalı

  // Wi-Fi'ye bağlan
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  // Bağlantı başarılı olduğunda IP adresini yazdır
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  // Sunucuyu başlat
  server.begin();
}

void loop() {
  WiFiClient client = server.available(); // Gelen bir istemci var mı diye dinle

  if (client) {
    Serial.println("New Client.");
    String currentLine = "";
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        Serial.write(c);
        if (c == '\n') {
          if (currentLine.length() == 0) {
            // HTTP isteği bitti, cevap gönder
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println();
            client.println("<html><body><h1>ESP32 Lamba Kontrol</h1></body></html>");
            client.println();
            break;
          } else {
            currentLine = "";
          }
        } else if (c != '\r') {
          currentLine += c;
        }

        // URL'yi kontrol et ve röleyi yönet
        if (currentLine.endsWith("GET /ac")) {
          Serial.println("KOMUT: AC");
          digitalWrite(RELAY_PIN, HIGH);
        }
        if (currentLine.endsWith("GET /kapat")) {
          Serial.println("KOMUT: KAPAT");
          digitalWrite(RELAY_PIN, LOW);
        }
      }
    }
    // Bağlantıyı kapat
    client.stop();
    Serial.println("Client Disconnected.");
  }
}