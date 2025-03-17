/*

 PANDA-BEAR Arduino Controller

 This Arduino sketch controls hardware components for the PANDA-BEAR system:
 - NeoPixel LED ring for illumination
 - Line break sensor for detection
 - Electromagnet for vial cap handling
 - Status LEDs for sample lighting, contact angle measurements, and feeback.
 - OpenTrons pipette motor and limit switch control

 Serial Protocol:
 Commands:
  1 (CMD_WHITE_ON): Turn on white LEDs
  2 (CMD_WHITE_OFF): Turn off white LEDs
  3 (CMD_CONTACT_ON): Turn on contact angle LEDs
  4 (CMD_CONTACT_OFF): Turn off contact angle LEDs
  5 (CMD_EMAG_ON): Turn on electromagnet
  6 (CMD_EMAG_OFF): Turn off electromagnet
  7 (CMD_LINE_BREAK): Check line break sensor
  8 (CMD_LINE_TEST): Test line break sensor
  9 (CMD_PIPETTE_HOME): Home the pipette
  10 (CMD_PIPETTE_MOVE): Move pipette to position
  11 (CMD_PIPETTE_ASPIRATE): Aspirate liquid
  12 (CMD_PIPETTE_DISPENSE): Dispense liquid
  13 (CMD_PIPETTE_STATUS): Get pipette position and status
  99 (CMD_HELLO): Test serial connection

 Responses:
  101 (RESP_WHITE_ON): White LEDs turned on
  102 (RESP_WHITE_OFF): White LEDs turned off
  103 (RESP_CONTACT_ON): Contact angle LEDs turned on
  104 (RESP_CONTACT_OFF): Contact angle LEDs turned off
  105 (RESP_EMAG_ON): Electromagnet turned on
  106 (RESP_EMAG_OFF): Electromagnet turned off
  107 (RESP_LINE_BREAK): Line break sensor triggered
  108 (RESP_LINE_UNBROKEN): Line break sensor untriggered
  109 (RESP_PIPETTE_HOMED): Pipette homed successfully
  110 (RESP_PIPETTE_MOVED): Pipette moved to position
  111 (RESP_PIPETTE_ASPIRATED): Pipette aspirated liquid
  112 (RESP_PIPETTE_DISPENSED): Pipette dispensed liquid
  113 (RESP_PIPETTE_STATUS): Pipette position and status
  999 (RESP_HELLO): Serial connection test

 Serial Configuration:
 Baud Rate: 115200
 Format: ASCII

 Author: Gregory Robben
 Last Updated: March 2025


*/

// Include Libraries
#include <Adafruit_NeoPixel.h>
#include <stdint.h>
#include <AccelStepper.h>
#include <ezButton.h>

// Definitions
#define LEDR_2_PIN 6
#define NEOPIXEL_RING_PIN 2
#define EMAG 3
#define NUMPIXELS 24
#define LINEBREAKLED 7
#define SENSORPIN 4
#define SENSITIVITY 100
#define SERIAL_TIMEOUT 1000 // ms
#define SERIAL_BAUD 115200

// Pipette motor pins and constants
#define PIPETTE_STEP_PIN 9
#define PIPETTE_DIR_PIN 8
#define PIPETTE_LIMIT_PIN 10
#define PIPETTE_MAX_POSITION 100.0 // Maximum travel in mm
#define PIPETTE_STEPS_PER_MM 200   // For Gen2 pipette (48 for Gen1)
#define PIPETTE_MAX_SPEED 10000    // Steps per second
#define PIPETTE_ACCELERATION 800   // Steps per second per second
#define PIPETTE_HOMING_SPEED 2000  // Lower speed for homing

// Message Definitions
enum CommandCodes
{
  CMD_WHITE_ON = 1,
  CMD_WHITE_OFF = 2,
  CMD_CONTACT_ON = 3,
  CMD_CONTACT_OFF = 4,
  CMD_EMAG_ON = 5,
  CMD_EMAG_OFF = 6,
  CMD_LINE_BREAK = 7,
  CMD_LINE_TEST = 8,
  CMD_PIPETTE_HOME = 9,
  CMD_PIPETTE_MOVE = 10,
  CMD_PIPETTE_ASPIRATE = 11,
  CMD_PIPETTE_DISPENSE = 12,
  CMD_PIPETTE_STATUS = 13,
  CMD_HELLO = 99
};

enum ResponseCodes
{
  RESP_WHITE_ON = 101,
  RESP_WHITE_OFF = 102,
  RESP_CONTACT_ON = 103,
  RESP_CONTACT_OFF = 104,
  RESP_EMAG_ON = 105,
  RESP_EMAG_OFF = 106,
  RESP_LINE_BREAK = 107,
  RESP_LINE_UNBROKEN = 108,
  RESP_PIPETTE_HOMED = 109,
  RESP_PIPETTE_MOVED = 110,
  RESP_PIPETTE_ASPIRATED = 111,
  RESP_PIPETTE_DISPENSED = 112,
  RESP_PIPETTE_STATUS = 113,
  RESP_HELLO = 999
};

// object initialization
Adafruit_NeoPixel ring(NUMPIXELS, NEOPIXEL_RING_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel dot_1(1, LEDR_2_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel dot_2(2, LEDR_2_PIN, NEO_GRB + NEO_KHZ800);

// variables will change:
int sensorState = 0,
    lastState = 0; // variable for reading the pushbutton status

// Initialize stepper motor and limit switch
AccelStepper pipetteStepper(AccelStepper::DRIVER, PIPETTE_STEP_PIN, PIPETTE_DIR_PIN);
ezButton pipetteLimitSwitch(PIPETTE_LIMIT_PIN);

// Pipette state variables
bool pipetteIsHomed = false;
float pipettePosition = 0.0; // Position in mm
float pipetteVolume = 0.0;   // Volume in µL

// Forward declarations
void ringTest();
void ringFill(uint32_t color);
void lineBreakTest();
void sendResponse(int code, bool success = true);
bool verifyPinState(uint8_t pin, uint8_t expectedState);
bool verifyNeoPixelState(Adafruit_NeoPixel &pixels, uint8_t pixel, uint32_t expectedColor);
void homePipette();
bool movePipetteToPosition(float position);
bool aspiratePipette(float volume);
bool dispensePipette(float volume);
void getPipetteStatus();

/*
Set up the Arduino board and initialize the hardware components
- Initialize serial communication
- Set pin modes for LEDs, electromagnet, and sensor
- Initialize NeoPixel ring
- Perform ring test
- Initialize line break sensor LED based on initial state
- Initialize pipette stepper motor and limit switch
*/
void setup()
{
  // initialize serial communication:
  Serial.begin(SERIAL_BAUD);
  while (!Serial)
    ; // wait for serial port to connect
  Serial.println("OK");
  pinMode(EMAG, OUTPUT);
  pinMode(LINEBREAKLED, OUTPUT);
  pinMode(SENSORPIN, INPUT);
  digitalWrite(SENSORPIN, HIGH); // turn on the pullup

  // Initialize NeoPixel dots
  dot_1.begin();
  dot_1.setBrightness(500); // adjust brightness here
  dot_1.show();             // Initialize all pixels to 'off'
  dot_2.begin();
  dot_2.setBrightness(500); // adjust brightness here
  dot_2.show();             // Initialize all pixels to 'off'

  // Initialize NeoPixel ring
  ring.begin();
  ring.setBrightness(500); // adjust brightness here
  ring.show();             // Initialize all pixels to 'off'

  ringTest();
  ring.clear();
  ring.show();

  // Initialize LINEBREAKLED based on the initial state of the sensor
  sensorState = digitalRead(SENSORPIN);
  if (sensorState == LOW)
  {
    digitalWrite(LINEBREAKLED, HIGH);
  }
  else
  {
    digitalWrite(LINEBREAKLED, LOW);
  }
  lastState = sensorState;

  // Initialize pipette limit switch
  pipetteLimitSwitch.setDebounceTime(50); // 50ms debounce time

  // Initialize pipette stepper motor
  pipetteStepper.setMaxSpeed(PIPETTE_MAX_SPEED);
  pipetteStepper.setAcceleration(PIPETTE_ACCELERATION);
  pipetteStepper.setCurrentPosition(0);
}

/*
Light up each ring LED on then off, one at a time, then make sure the ring is clear
*/
void ringTest()
{
  for (int i = 0; i < ring.numPixels(); i++)
  {
    ring.setPixelColor(i, ring.Color(0, 0, 255)); //  Set pixel's color
    ring.show();
    delay(500);
    ring.setPixelColor(i, 0); // Turn off the pixel after delay
  }
  ring.clear();
  Serial.println("Ring Test Complete");
}

/*
Set all ring LEDs to a specific color
*/
void ringFill(uint32_t color)
{
  for (int i = 0; i < ring.numPixels(); i++)
  {                               // For each pixel in strip...
    ring.setPixelColor(i, color); //  Set pixel's color (in RAM)
    ring.show();
  }
}

/*
Test the line break sensor and update the LED states based on the sensor state
Self limit to 10 loops
*/
void lineBreakTest()
{
  for (int i = 0; i < 10; i++)
  { // Run for 10 cycles only
    sensorState = digitalRead(SENSORPIN);

    // Update LED states
    if (sensorState == LOW)
    { // Beam broken
      digitalWrite(LINEBREAKLED, HIGH);
      dot_1.setPixelColor(0, dot_1.Color(255, 0, 0)); // First dot red
      dot_2.setPixelColor(0, dot_2.Color(255, 0, 0)); // Second dot red
      dot_1.show();
      dot_2.show();
      Serial.println("beam roken");
    }
    else
    { // Beam unbroken
      digitalWrite(LINEBREAKLED, LOW);
      dot_1.clear(); // Turn off both dots
      dot_2.clear();
      dot_1.show();
      dot_2.show();
      Serial.println("beam unbroken");
    }

    // Report state changes
    if (sensorState != lastState)
    {
      Serial.println(sensorState == HIGH ? "108" : "107");
      lastState = sensorState;
    }

    delay(100); // Small delay between readings
  }
}

void sendResponse(int code, bool success = true)
{
  Serial.print(success ? "OK:" : "ERR:");
  Serial.println(code); // Send the response code
}

// Add after other function declarations
bool verifyPinState(uint8_t pin, uint8_t expectedState)
{
  // Read the actual pin state and compare with expected state
  return digitalRead(pin) == expectedState;
}

// Add a new function to verify NeoPixel LED state
bool verifyNeoPixelState(Adafruit_NeoPixel &pixels, uint8_t pixel, uint32_t expectedColor)
{
  // Read the actual NeoPixel color and compare with expected color
  return pixels.getPixelColor(pixel) == expectedColor;
}

/*
 * Home the pipette by moving until the limit switch is triggered
 * This simulates the homing routine from the Duet configuration
 */
void homePipette()
{
  // First ensure the limit switch is initialized
  pipetteLimitSwitch.loop();

  // Set a slower speed for homing
  pipetteStepper.setMaxSpeed(PIPETTE_HOMING_SPEED);

  Serial.println("Homing pipette...");

  // Move in positive direction until limit switch is hit
  // (This matches the direction in the Duet config where the motor moves towards the endstop)
  while (pipetteLimitSwitch.getState() == HIGH)
  {
    pipetteStepper.move(100); // Move a bit at a time
    pipetteStepper.run();
    pipetteLimitSwitch.loop(); // Update limit switch state

    // Add a small delay to not block completely
    delay(1);
  }

  // Stop the motor
  pipetteStepper.stop();

  // Back off from the limit switch
  pipetteStepper.move(-100); // Move away from switch in negative direction
  while (pipetteStepper.distanceToGo() != 0)
  {
    pipetteStepper.run();
  }

  // Find switch again at slower speed for precision
  pipetteStepper.setMaxSpeed(PIPETTE_HOMING_SPEED / 2);
  while (pipetteLimitSwitch.getState() == HIGH)
  {
    pipetteStepper.move(10); // Smaller movements
    pipetteStepper.run();
    pipetteLimitSwitch.loop();
    delay(1);
  }

  // Set this position as zero
  pipetteStepper.setCurrentPosition(0);
  pipettePosition = 0.0;
  pipetteVolume = 0.0;
  pipetteIsHomed = true;

  // Reset to normal speed
  pipetteStepper.setMaxSpeed(PIPETTE_MAX_SPEED);

  // Move to a safe starting position (0.5mm)
  movePipetteToPosition(0.5);

  sendResponse(RESP_PIPETTE_HOMED, true);
}

/*
 * Move pipette to specific position in mm
 */
bool movePipetteToPosition(float position)
{
  if (!pipetteIsHomed)
  {
    Serial.println("ERROR: Pipette not homed");
    return false;
  }

  // Check if position is within bounds
  if (position < 0 || position > PIPETTE_MAX_POSITION)
  {
    Serial.println("ERROR: Position out of bounds");
    return false;
  }

  // Convert mm to steps
  long targetSteps = position * PIPETTE_STEPS_PER_MM;

  // Move to position
  pipetteStepper.moveTo(targetSteps);

  // Wait for move to complete
  while (pipetteStepper.distanceToGo() != 0)
  {
    pipetteStepper.run();
  }

  // Update current position
  pipettePosition = position;

  return true;
}

/*
 * Aspirate a specific volume (move pipette plunger down)
 * Note: This is a simplification - actual calibration would be needed
 * to map volume to distance for accurate pipetting
 */
bool aspiratePipette(float volume)
{
  if (!pipetteIsHomed)
  {
    Serial.println("ERROR: Pipette not homed");
    return false;
  }

  // For simplicity, assume 1mm = 10µL (this would need calibration)
  float targetPosition = pipettePosition + (volume / 10.0);

  // Check if aspiration would exceed max position
  if (targetPosition > PIPETTE_MAX_POSITION)
  {
    Serial.println("ERROR: Requested volume exceeds pipette capacity");
    return false;
  }

  // Move to new position
  bool success = movePipetteToPosition(targetPosition);

  if (success)
  {
    pipetteVolume += volume;
  }

  return success;
}

/*
 * Dispense a specific volume (move pipette plunger up)
 */
bool dispensePipette(float volume)
{
  if (!pipetteIsHomed)
  {
    Serial.println("ERROR: Pipette not homed");
    return false;
  }

  // Check if we have enough volume to dispense
  if (volume > pipetteVolume)
  {
    Serial.println("ERROR: Not enough volume in pipette");
    return false;
  }

  // For simplicity, assume 1mm = 10µL (this would need calibration)
  float targetPosition = pipettePosition - (volume / 10.0);

  // Check if dispense would go below min position
  if (targetPosition < 0)
  {
    Serial.println("ERROR: Dispense would exceed minimum position");
    return false;
  }

  // Move to new position
  bool success = movePipetteToPosition(targetPosition);

  if (success)
  {
    pipetteVolume -= volume;
  }

  return success;
}

/*
 * Report current pipette status (position, volume, homed state)
 */
void getPipetteStatus()
{
  Serial.print("STATUS:");
  Serial.print(pipetteIsHomed ? "1," : "0,");
  Serial.print(pipettePosition, 2);
  Serial.print(",");
  Serial.println(pipetteVolume, 2);
  sendResponse(RESP_PIPETTE_STATUS, true);
}

/*
Main loop for the Arduino controller
- Check for incoming serial commands
- Execute commands based on the command code
- Send responses based on the command code
*/
void loop()
{
  // Update limit switch state
  pipetteLimitSwitch.loop();

  // Process any pending stepper movements
  pipetteStepper.run();

  while (Serial.available() > 0)
  {
    int command = Serial.parseInt();

    switch (command)
    {
    case CMD_WHITE_ON:
      ringFill(ring.Color(255, 255, 255)); // White
      sendResponse(RESP_WHITE_ON);
      break;
    case CMD_WHITE_OFF:
      ring.clear();
      ring.show();
      sendResponse(RESP_WHITE_OFF);
      break;
    case CMD_CONTACT_ON:
      // Set dots for contact angle measurement
      dot_1.setPixelColor(0, dot_1.Color(255, 0, 0)); // First dot (was LEDR_1)
      dot_2.setPixelColor(0, dot_2.Color(255, 0, 0)); // Second dot (was LEDR_2)
      dot_1.show();
      dot_2.show();
      // Also set ring pixels for visual feedback
      ring.setPixelColor(6, ring.Color(0, 0, 255)); // Blue
      ring.setPixelColor(18, ring.Color(0, 0, 255));
      ring.show();

      // Verify NeoPixel dots are on with red color
      sendResponse(RESP_CONTACT_ON,
                   verifyNeoPixelState(dot_1, 0, dot_1.Color(255, 0, 0)) && verifyNeoPixelState(dot_2, 0, dot_2.Color(255, 0, 0)));
      break;
    case CMD_CONTACT_OFF:
      // Turn off both dots
      dot_1.clear();
      dot_2.clear();
      dot_1.show();
      dot_2.show();

      // Clear the ring as well
      ring.clear();
      ring.show();

      // Verify NeoPixel dots are off
      sendResponse(RESP_CONTACT_OFF,
                   verifyNeoPixelState(dot_1, 0, 0) && verifyNeoPixelState(dot_2, 0, 0));
      break;
    case CMD_EMAG_ON:
      digitalWrite(EMAG, HIGH);
      sendResponse(RESP_EMAG_ON, verifyPinState(EMAG, HIGH));
      break;
    case CMD_EMAG_OFF:
      digitalWrite(EMAG, LOW);
      sendResponse(RESP_EMAG_OFF, verifyPinState(EMAG, LOW));
      break;
    case CMD_LINE_BREAK:
      if (digitalRead(SENSORPIN) == LOW)
      {
        Serial.println("107"); // Line break sensor triggered
      }
      else
      {
        Serial.println("108"); // Line break sensor untriggered (unbroken)
      }
      break;

    case CMD_LINE_TEST:
      lineBreakTest();
      break;

    case CMD_PIPETTE_HOME:
      homePipette();
      break;

    case CMD_PIPETTE_MOVE:
      // Expect a float parameter for position in mm
      while (Serial.available() == 0)
        delay(10);
      float targetPosition = Serial.parseFloat();
      bool moveSuccess = movePipetteToPosition(targetPosition);
      sendResponse(RESP_PIPETTE_MOVED, moveSuccess);
      break;

    case CMD_PIPETTE_ASPIRATE:
      // Expect a float parameter for volume in µL
      while (Serial.available() == 0)
        delay(10);
      float aspirateVolume = Serial.parseFloat();
      bool aspirateSuccess = aspiratePipette(aspirateVolume);
      sendResponse(RESP_PIPETTE_ASPIRATED, aspirateSuccess);
      break;

    case CMD_PIPETTE_DISPENSE:
      // Expect a float parameter for volume in µL
      while (Serial.available() == 0)
        delay(10);
      float dispenseVolume = Serial.parseFloat();
      bool dispenseSuccess = dispensePipette(dispenseVolume);
      sendResponse(RESP_PIPETTE_DISPENSED, dispenseSuccess);
      break;

    case CMD_PIPETTE_STATUS:
      getPipetteStatus();
      break;

    case CMD_HELLO:
      Serial.println("999");
      break;
    default:
      Serial.println(-1);
    }

    // Clear the serial buffer
    while (Serial.available() > 0)
    {
      Serial.read();
    }
  }
}