// The pawduino sketch is the main sketch that runs on the Arduino. It is responsible
// for listening for commands from the computer, and sending confirmation.
// Currently features include: turning on/off white LEDs, turning on/off red LEDs, turning on/off 5V electromagnet

// libraries
// Include Libraries
#include "Arduino.h"
#include "Adafruit_NeoPixel.h"

// Pin Definitions
#define LEDR_1_PIN 5
#define LEDR_2_PIN 6
#define NEOPIXEL_RING_PIN 2
#define EMAG 3

// Message Definitions
/*white leds */
#define wo 1
#define wf 2
/*red leds*/
#define co 3
#define cf 4
/*electromagnet*/
#define eo 5
#define ef 6
/*hello message*/
#define hello 99

// Global variables and defines
#define NUMPIXELS 16
// object initialization
Adafruit_NeoPixel ring(NUMPIXELS, NEOPIXEL_RING_PIN, NEO_GRB + NEO_KHZ800);

void setup()
{
  // initialize serial communication:
  Serial.begin(115200);
  while (!Serial)
    ; // wait for serial port to connect
  Serial.println("OK");
  pinMode(EMAG, OUTPUT);
  pinMode(LEDR_1_PIN, OUTPUT);
  pinMode(LEDR_2_PIN, OUTPUT);
  ring.begin();
  ring.setBrightness(500); // adjust brightness here
  ring.show();            // Initialize all pixels to 'off'
}

void ringFill(uint32_t color)
{
  for (int i = 0; i < ring.numPixels(); i++)
  {                               // For each pixel in strip...
    ring.setPixelColor(i, color); //  Set pixel's color (in RAM)
  }
  ring.show();
}

void loop()
{
  // if there's any serial available, read it:
  while (Serial.available() > 0)
  {
    // look for the next valid integer in the incoming serial stream:
    int command = Serial.parseInt();

    switch (command)
    {
    case wo:
      ringFill(ring.Color(255, 255, 255)); // White
      Serial.println("101");
      break;
    case wf:
      ring.clear();
      ring.show();
      Serial.println("102");
      break;
    case co:
      digitalWrite(LEDR_1_PIN, HIGH); // turn on red LED
      digitalWrite(LEDR_2_PIN, HIGH);
      ringFill(ring.Color(255, 255, 255)); // White
      ring.setPixelColor(0, ring.Color(0, 0, 255)); // Blue
      ring.setPixelColor(8, ring.Color(0, 0, 255));
      ring.show();
      Serial.println("103");
      break;
    case cf:
      digitalWrite(LEDR_1_PIN, LOW);
      digitalWrite(LEDR_2_PIN, LOW);
      ring.clear();
      ring.show();
      Serial.println("104");
      break;
    case eo:
      digitalWrite(EMAG, HIGH);
      Serial.println("105");
      break;
    case ef:
      digitalWrite(EMAG, LOW);
      Serial.println("106");
      break;
    case hello:
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
