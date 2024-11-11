// Arduino Code with both LCD and Serial Communication
#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <Adafruit_Fingerprint.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial1);

#define openLight 8
#define closeLight 9
#define redled 10
#define relay 11
#define sensor A0

void setup() {
  pinMode(openLight, OUTPUT);
  pinMode(relay, OUTPUT);
  pinMode(closeLight, OUTPUT);
  pinMode(sensor, INPUT);
  pinMode(redled, OUTPUT);

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("System Starting");
  lcd.setCursor(0, 1);
  lcd.print("Please Wait...");
  
  Serial.begin(9600);     // Communication with Raspberry Pi
  Serial1.begin(57600);   // Fingerprint sensor
  finger.begin(57600);
  
  if (!finger.verifyPassword()) {
    Serial.println("ERROR:FP_NOT_FOUND");
    lcd.clear();
    lcd.print("Sensor Error!");
    lcd.setCursor(0, 1);
    lcd.print("Check Connection");
    while (1);
  }
  
  lcd.clear();
  lcd.print("System Ready");
  Serial.println("READY");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  checkAlcoholLevel();
  delay(100);
}

void checkAlcoholLevel() {
  float adcValue = 0;
  for (int i = 0; i < 10; i++) {
    adcValue += analogRead(sensor);
    delay(10);
  }
  float v = (adcValue / 10) * (3.3 / 1024.0);
  float mgL = 0.67 * v;
  
  Serial.print("BAC:");
  Serial.println(mgL);
  
  // Update LCD with BAC level
  lcd.setCursor(0, 1);
  lcd.print("BAC: ");
  lcd.print(mgL, 2);
  lcd.print(" mg/L    ");
  
  if (mgL > 1.3) {
    digitalWrite(redled, HIGH);
    digitalWrite(relay, LOW);
    digitalWrite(openLight, LOW);
    Serial.println("STATUS:DRUNK");
    lcd.clear();
    lcd.print("Access Denied!");
    lcd.setCursor(0, 1);
    lcd.print("Driver Drunk!");
  } else {
    digitalWrite(redled, LOW);
    Serial.println("STATUS:NORMAL");
  }
}

void processCommand(String command) {
  if (command.startsWith("ENROLL:")) {
    int id = command.substring(7).toInt();
    enrollFingerprint(id);
  }
  else if (command.startsWith("DELETE:")) {
    int id = command.substring(7).toInt();
    deleteFingerprint(id);
  }
  else if (command == "SCAN") {
    scanFingerprint();
  }
}

void enrollFingerprint(int id) {
  Serial.println("ENROLL_START");
  lcd.clear();
  lcd.print("Enrolling ID:");
  lcd.setCursor(0, 1);
  lcd.print(id);
  
  while (!getFingerprintEnroll(id)) {
    delay(100);
  }
  
  lcd.clear();
  lcd.print("Enrollment Done!");
  Serial.println("ENROLL_COMPLETE");
  delay(2000);
  lcd.clear();
  lcd.print("System Ready");
}

void scanFingerprint() {
  lcd.clear();
  lcd.print("Place Finger");
  int result = getFingerprintIDez();
  
  if (result >= 0) {
    Serial.print("MATCH:");
    Serial.println(result);
    lcd.clear();
    lcd.print("Access Granted!");
    lcd.setCursor(0, 1);
    lcd.print("ID: ");
    lcd.print(result);
    
    digitalWrite(openLight, HIGH);
    digitalWrite(relay, HIGH);
    digitalWrite(closeLight, LOW);
    delay(2000);
    digitalWrite(openLight, LOW);
    digitalWrite(relay, LOW);
    digitalWrite(closeLight, HIGH);
  } else {
    Serial.println("NO_MATCH");
    lcd.clear();
    lcd.print("Access Denied!");
    lcd.setCursor(0, 1);
    lcd.print("No Match Found");
    delay(2000);
  }
  
  lcd.clear();
  lcd.print("System Ready");
}

bool getFingerprintEnroll(uint8_t id) {
  int p = finger.getImage();
  if (p != FINGERPRINT_OK) return false;
  
  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) return false;
  
  Serial.println("REMOVE_FINGER");
  lcd.clear();
  lcd.print("Remove Finger");
  delay(2000);
  
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }
  
  Serial.println("PLACE_AGAIN");
  lcd.clear();
  lcd.print("Place Same");
  lcd.setCursor(0, 1);
  lcd.print("Finger Again");
  
  p = -1;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
  }
  
  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) return false;
  
  p = finger.createModel();
  if (p != FINGERPRINT_OK) return false;
  
  p = finger.storeModel(id);
  if (p != FINGERPRINT_OK) return false;
  
  return true;
}

int getFingerprintIDez() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK) return -1;
  
  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return -1;
  
  p = finger.fingerFastSearch();
  if (p != FINGERPRINT_OK) return -1;
  
  return finger.fingerID;
}

uint8_t deleteFingerprint(uint8_t id) {
  uint8_t p = finger.deleteModel(id);
  lcd.clear();
  if (p == FINGERPRINT_OK) {
    Serial.println("DELETE_SUCCESS");
    lcd.print("ID ");
    lcd.print(id);
    lcd.print(" Deleted!");
  } else {
    Serial.println("DELETE_FAILED");
    lcd.print("Delete Failed!");
  }
  delay(2000);
  lcd.clear();
  lcd.print("System Ready");
  return p;
}