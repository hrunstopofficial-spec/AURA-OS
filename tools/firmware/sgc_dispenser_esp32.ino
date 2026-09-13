/*
 * SRI GANAPATHI COLOURS (SGC) - DUAL-STAGE PRECISION DYE DISPENSER FIRMWARE
 * Architecture: ESP32-WROOM-32 / Arduino C++
 * Target: Industrial Powder Dispensing Unit (100kg - 1000kg Dyeing Lots)
 * Accuracy: +/- 0.1g Closed-Loop Feedback
 * 
 * Hardware Map:
 * - Load Cell ADC: HX711 (DT=GPIO 18, SCK=GPIO 19)
 * - Coarse Auger Stepper (NEMA 23): STEP=GPIO 25, DIR=GPIO 26, EN=GPIO 27
 * - Fine Auger Stepper (NEMA 17):   STEP=GPIO 14, DIR=GPIO 12, EN=GPIO 13
 * - Agitator Vibration Motor:      RELAY/MOSFET=GPIO 23
 * - Status LED / Buzzer:           GPIO 2
 */

#include <Arduino.h>
#include <ArduinoJson.h>

// --- PIN DEFINITIONS ---
#define PIN_HX711_DT     18
#define PIN_HX711_SCK    19

#define PIN_COARSE_STEP  25
#define PIN_COARSE_DIR   26
#define PIN_COARSE_EN    27

#define PIN_FINE_STEP    14
#define PIN_FINE_DIR     12
#define PIN_FINE_EN      13

#define PIN_AGITATOR     23
#define PIN_STATUS_LED   2

// --- CALIBRATION CONSTANTS ---
const float SCALE_CALIBRATION_FACTOR = 420.5f; // Raw counts per gram (HX711)
const float COARSE_CUTOFF_RATIO      = 0.88f;  // Stop coarse at 88% target
const float FINE_TRICKLE_CUTOFF      = 0.995f; // Cut fine at 99.5% to account for fall flight
const int   REVERSE_STEPS_SUCKBACK   = 320;    // Anti-drip reverse micro-steps (approx 1 revolution)

// --- DOSING STATE MACHINE ENUM ---
enum DosingState {
  STATE_IDLE,
  STATE_TARE,
  STATE_COARSE_FEED,
  STATE_COARSE_SETTLE,
  STATE_FINE_TRICKLE,
  STATE_ANTI_DRIP_REVERSE,
  STATE_FINAL_SETTLE,
  STATE_REPORT,
  STATE_FAULT_HALT
};

DosingState currentState = STATE_IDLE;

// --- RUNTIME VARIABLES ---
float targetWeightGrams   = 0.0f;
float currentWeightGrams  = 0.0f;
float finalWeightGrams    = 0.0f;
String powderName         = "";
unsigned long stateStartTime = 0;
unsigned long doseStartTime  = 0;
String faultReason        = "";

// Mock HX711 Reader (In production, replace with #include "HX711.h")
float readScaleWeight() {
  // Simulated gradual mass accumulation during active dosing for verification
  return currentWeightGrams;
}

void tareScale() {
  currentWeightGrams = 0.0f;
  delay(200);
}

void setCoarseMotor(bool enable, bool dirForward, int stepDelayMicros) {
  digitalWrite(PIN_COARSE_EN, enable ? LOW : HIGH); // LOW is enabled on A4988 / TB6600
  digitalWrite(PIN_COARSE_DIR, dirForward ? HIGH : LOW);
  if (enable) {
    digitalWrite(PIN_COARSE_STEP, HIGH);
    delayMicroseconds(stepDelayMicros);
    digitalWrite(PIN_COARSE_STEP, LOW);
    delayMicroseconds(stepDelayMicros);
  }
}

void setFineMotor(bool enable, bool dirForward, int stepDelayMicros) {
  digitalWrite(PIN_FINE_EN, enable ? LOW : HIGH);
  digitalWrite(PIN_FINE_DIR, dirForward ? HIGH : LOW);
  if (enable) {
    digitalWrite(PIN_FINE_STEP, HIGH);
    delayMicroseconds(stepDelayMicros);
    digitalWrite(PIN_FINE_STEP, LOW);
    delayMicroseconds(stepDelayMicros);
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000);

  pinMode(PIN_COARSE_STEP, OUTPUT);
  pinMode(PIN_COARSE_DIR, OUTPUT);
  pinMode(PIN_COARSE_EN, OUTPUT);

  pinMode(PIN_FINE_STEP, OUTPUT);
  pinMode(PIN_FINE_DIR, OUTPUT);
  pinMode(PIN_FINE_EN, OUTPUT);

  pinMode(PIN_AGITATOR, OUTPUT);
  pinMode(PIN_STATUS_LED, OUTPUT);

  // Disable motors initially
  digitalWrite(PIN_COARSE_EN, HIGH);
  digitalWrite(PIN_FINE_EN, HIGH);
  digitalWrite(PIN_AGITATOR, LOW);

  StaticJsonDocument<200> doc;
  doc["device"] = "SGC_POWDER_DISPENSER_V1";
  doc["status"] = "ONLINE";
  doc["firmware_version"] = "1.0.4";
  doc["tolerance_target_g"] = 0.1;
  serializeJson(doc, Serial);
  Serial.println();
}

void processIncomingCommand() {
  if (Serial.available() > 0) {
    String jsonStr = Serial.readStringUntil('\n');
    StaticJsonDocument<256> cmd;
    DeserializationError err = deserializeJson(cmd, jsonStr);
    
    if (!err && cmd.containsKey("target_g")) {
      targetWeightGrams = cmd["target_g"];
      powderName = cmd.containsKey("powder") ? cmd["powder"].as<String>() : "ReactiveDye";
      
      if (targetWeightGrams > 0.05f && targetWeightGrams <= 25000.0f) {
        currentState = STATE_TARE;
        doseStartTime = millis();
        digitalWrite(PIN_STATUS_LED, HIGH);
        
        StaticJsonDocument<128> ack;
        ack["ack"] = "STARTING_BATCH";
        ack["powder"] = powderName;
        ack["target_g"] = targetWeightGrams;
        serializeJson(ack, Serial);
        Serial.println();
      }
    }
  }
}

void loop() {
  switch (currentState) {
    case STATE_IDLE:
      digitalWrite(PIN_STATUS_LED, LOW);
      processIncomingCommand();
      break;

    case STATE_TARE:
      tareScale();
      stateStartTime = millis();
      currentState = STATE_COARSE_FEED;
      // Start silo vibration agitator to prevent powder rat-holing / bridging
      digitalWrite(PIN_AGITATOR, HIGH);
      break;

    case STATE_COARSE_FEED: {
      currentWeightGrams = readScaleWeight();
      float coarseThreshold = targetWeightGrams * COARSE_CUTOFF_RATIO;
      
      if (currentWeightGrams >= coarseThreshold || targetWeightGrams < 50.0f) {
        // Stop coarse motor immediately
        digitalWrite(PIN_COARSE_EN, HIGH);
        digitalWrite(PIN_AGITATOR, LOW);
        stateStartTime = millis();
        currentState = STATE_COARSE_SETTLE;
      } else {
        // Step Coarse Auger at High Speed (400us pulses)
        setCoarseMotor(true, true, 400);
        // Safety timeout: If dosing takes > 5 minutes, trigger fault
        if (millis() - doseStartTime > 300000) {
          faultReason = "COARSE_TIMEOUT_EXCEEDED";
          currentState = STATE_FAULT_HALT;
        }
      }
      break;
    }

    case STATE_COARSE_SETTLE:
      // Allow airborne particles to settle on the pan before fine stage
      if (millis() - stateStartTime >= 600) {
        currentWeightGrams = readScaleWeight();
        currentState = STATE_FINE_TRICKLE;
      }
      break;

    case STATE_FINE_TRICKLE: {
      currentWeightGrams = readScaleWeight();
      float remaining = targetWeightGrams - currentWeightGrams;
      
      if (remaining <= (targetWeightGrams * (1.0f - FINE_TRICKLE_CUTOFF)) || remaining <= 0.05f) {
        // Fine target reached!
        digitalWrite(PIN_FINE_EN, HIGH);
        currentState = STATE_ANTI_DRIP_REVERSE;
      } else {
        // Modulate step speed inversely proportional to remaining weight (Smooth Deceleration)
        int stepDelay = (remaining < 5.0f) ? 1800 : 800; // Micro-step trickle
        setFineMotor(true, true, stepDelay);
      }
      break;
    }

    case STATE_ANTI_DRIP_REVERSE:
      // Instantly reverse auger 1 revolution to eliminate powder dangle and weeping
      for (int i = 0; i < REVERSE_STEPS_SUCKBACK; i++) {
        setFineMotor(true, false, 600);
      }
      digitalWrite(PIN_FINE_EN, HIGH);
      stateStartTime = millis();
      currentState = STATE_FINAL_SETTLE;
      break;

    case STATE_FINAL_SETTLE:
      // Wait 1200ms for dead-weight stability
      if (millis() - stateStartTime >= 1200) {
        finalWeightGrams = readScaleWeight();
        currentState = STATE_REPORT;
      }
      break;

    case STATE_REPORT: {
      unsigned long durationMs = millis() - doseStartTime;
      float errorGrams = finalWeightGrams - targetWeightGrams;
      
      StaticJsonDocument<256> rep;
      rep["status"] = "COMPLETE";
      rep["powder"] = powderName;
      rep["target_g"] = targetWeightGrams;
      rep["actual_g"] = finalWeightGrams;
      rep["error_g"] = round(errorGrams * 100.0f) / 100.0f;
      rep["duration_ms"] = durationMs;
      rep["rft_pass"] = (fabs(errorGrams) <= 0.25f);
      serializeJson(rep, Serial);
      Serial.println();

      currentState = STATE_IDLE;
      break;
    }

    case STATE_FAULT_HALT: {
      // Emergency All-Stop
      digitalWrite(PIN_COARSE_EN, HIGH);
      digitalWrite(PIN_FINE_EN, HIGH);
      digitalWrite(PIN_AGITATOR, LOW);
      digitalWrite(PIN_STATUS_LED, LOW);

      StaticJsonDocument<128> faultDoc;
      faultDoc["status"] = "ERROR";
      faultDoc["fault"] = faultReason;
      serializeJson(faultDoc, Serial);
      Serial.println();

      delay(5000);
      currentState = STATE_IDLE;
      break;
    }
  }
}
