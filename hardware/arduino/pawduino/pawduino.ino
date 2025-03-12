/*

 PANDA-BEAR Arduino Controller

 This Arduino sketch controls hardware components for the PANDA-BEAR system:
 - NeoPixel LED ring for illumination
 - Line break sensor for detection
 - Electromagnet for vial cap handling
 - Status LEDs for sample lighting, contact angle measurements, and feeback.

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
  999 (RESP_HELLO): Serial connection test

 Serial Configuration:
 Baud Rate: 115200
 Format: ASCII

 Author: Gregory Robben
 Last Updated: February 2025


*/

// Include Libraries
#include "Adafruit_NeoPixel.h"
#include <stdint.h>

// Definitions
#define LEDR_1_PIN 5
#define LEDR_2_PIN 6
#define NEOPIXEL_RING_PIN 2
#define EMAG 3
#define NUMPIXELS 24
#define LINEBREAKLED 7
#define SENSORPIN 4
#define SENSITIVITY 100
#define SERIAL_TIMEOUT 1000 // ms
#define SERIAL_BAUD 115200

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
  RESP_HELLO = 999
};

// object initialization
Adafruit_NeoPixel ring(NUMPIXELS, NEOPIXEL_RING_PIN, NEO_GRBW + NEO_KHZ800);

// variables will change:
int sensorState = 0,
    lastState = 0; // variable for reading the pushbutton status

/*
Set up the Arduino board and initialize the hardware components
- Initialize serial communication
- Set pin modes for LEDs, electromagnet, and sensor
- Initialize NeoPixel ring
- Perform ring test
- Initialize line break sensor LED based on initial state
*/
void setup()
{
  // initialize serial communication:
  Serial.begin(SERIAL_BAUD);
  while (!Serial)
    ; // wait for serial port to connect
  Serial.println("OK");
  pinMode(EMAG, OUTPUT);
  pinMode(LEDR_1_PIN, OUTPUT);
  pinMode(LEDR_2_PIN, OUTPUT);
  pinMode(LINEBREAKLED, OUTPUT);
  pinMode(SENSORPIN, INPUT);
  digitalWrite(SENSORPIN, HIGH); // turn on the pullup
  ring.begin();
  ring.setBrightness(100); // adjust brightness here
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
      digitalWrite(LEDR_1_PIN, HIGH);
      digitalWrite(LEDR_2_PIN, HIGH);
    }
    else
    { // Beam unbroken
      digitalWrite(LINEBREAKLED, LOW);
      digitalWrite(LEDR_1_PIN, LOW);
      digitalWrite(LEDR_2_PIN, LOW);
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

/*
Set the color of a specific ring LED
*/
void setRingLED(uint8_t pixel, uint32_t color)
{
  if (pixel < NUMPIXELS)
  {
    ring.setPixelColor(pixel, color);
    ring.show();
  }
}

/*
Turn off all ring LEDs
*/
void clearRing()
{
  ring.clear();
  ring.show();
}

// Add after other function declarations
bool verifyPinState(uint8_t pin, uint8_t expectedState)
{
  // Read the actual pin state and compare with expected state
  return digitalRead(pin) == expectedState;
}


/*
Main loop for the Arduino controller
- Check for incoming serial commands
- Execute commands based on the command code
- Send responses based on the command code
*/
void loop()
{
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
      digitalWrite(LEDR_1_PIN, HIGH);
      digitalWrite(LEDR_2_PIN, HIGH);
      ring.setPixelColor(6, ring.Color(0, 0, 255));
      ring.setPixelColor(18, ring.Color(0, 0, 255));
      ring.show();
      // Verify both LEDs are on
      sendResponse(RESP_CONTACT_ON,
                   verifyPinState(LEDR_1_PIN, HIGH) &&
                       verifyPinState(LEDR_2_PIN, HIGH));
      break;
    case CMD_CONTACT_OFF:
      digitalWrite(LEDR_1_PIN, LOW);
      digitalWrite(LEDR_2_PIN, LOW);
      ring.clear();
      ring.show();
      // Verify both LEDs are off
      sendResponse(RESP_CONTACT_OFF,
                   verifyPinState(LEDR_1_PIN, LOW) &&
                       verifyPinState(LEDR_2_PIN, LOW));
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
        Serial.println("107");
      }
      else
      {
        Serial.println("108");
      }
      break;

    case CMD_LINE_TEST:
      lineBreakTest();
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