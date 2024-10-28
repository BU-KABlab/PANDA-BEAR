// The pawduino sketch is the main sketch that runs on the Arduino. It is responsible
// for listening for commands from the computer, and sending confirmation.
// Currently features include: turning on/off white LEDs, turning on/off red LEDs, turning on/off 5V electromagnet

// libraries
#include <Arduino.h>

// white leds pin
/*white leds */
#define wo 1
#define wf 2
#define wled_pin 13 // TODO: change to correct pin for circuit
/*red leds*/
#define ro 3
#define rf 4
#define rled_pin 13 // TODO: change to correct pin for circuit
/*electromagnet*/
#define eo 5
#define ef 6
#define emag_pin 13 // TODO: change to correct pin for circuit

/*hello message - 99*/
#define hello 99

void setup()
{
  // initialize serial communication:
  Serial.begin(115200);
  // initialize the pins as an output:
  pinMode(wled_pin, OUTPUT);
  // pinMode(rled_pin, OUTPUT);
  // pinMode(emag_pin, OUTPUT);
}

void loop()
{
  // if there's any serial available, read it:
  while (Serial.available() > 0)
  {
    // look for the next valid integer in the incoming serial stream:
    int command = Serial.parseInt();
    // if (Serial.read() == '\n') {
    //     continue; // Ignore the newline character
    // }
    // do it!
    switch (command)
    {
    case wo:
      digitalWrite(wled_pin, HIGH);
      Serial.println(101);
      break;
    case wf:
      digitalWrite(wled_pin, LOW);
      Serial.println(102);
      break;
    case ro:
      digitalWrite(rled_pin, HIGH);
      Serial.println(103);
      break;
    case rf:
      digitalWrite(rled_pin, LOW);
      Serial.println(104);
      break;
    case eo:
      digitalWrite(emag_pin, HIGH);
      Serial.println(105);
      break;
    case ef:
      digitalWrite(emag_pin, LOW);
      Serial.println(106);
      break;

    case hello:
      Serial.println(999);
      break;
    default:
      Serial.println('recieved command: ' + command + ' is not recognized');
    }
  }
}
