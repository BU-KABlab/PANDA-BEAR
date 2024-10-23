// The pawduino sketch is the main sketch that runs on the Arduino. It is responsible
// for listening for commands from the computer, and sending confirmation.
// Currently features include: turning on/off white LEDs, turning on/off red LEDs, turning on/off 5V electromagnet

// libraries
#include <Arduino.h>

// white leds pin
/*white leds */
#define wo 0x01
#define wf 0x02
#define wled_pin 13
/*red leds*/
#define ro 0x03
#define rf 0x04
#define rled_pin 12
/*electromagnet*/
#define eo 0x05
#define ef 0x06
#define emag_pin 11

void setup() {
  // initialize serial communication:
  Serial.begin(115200);
    // initialize the pins as an output:
    pinMode(wled_pin, OUTPUT);
    pinMode(rled_pin, OUTPUT);
    pinMode(emag_pin, OUTPUT);
}

void loop() {
  // if there's any serial available, read it:
  while (Serial.available() > 0) {
    // look for the next valid integer in the incoming serial stream:
    int command = Serial.parseInt();
    // do it!
    switch (command) {
      case wo:
        digitalWrite(wled_pin, HIGH);
        Serial.println(1);
        break;
      case wf:
        digitalWrite(wled_pin, LOW);
        Serial.println(2);
        break;
      case ro:
        digitalWrite(rled_pin, HIGH);
        Serial.println(3);
        break;
      case rf:
        digitalWrite(rled_pin, LOW);
        Serial.println(4);
        break;
      case eo:
        digitalWrite(emag_pin, HIGH);
        Serial.println(5);
        break;
      case ef:
        digitalWrite(emag_pin, LOW);
        Serial.println(6);
        break;
      default:
        Serial.println(-1);
    }
  }
}

