// File: Pipette driver for Opentrons OT-2 Gen2
#include <Adafruit_MotorShield.h>
#include <ezButton.h>

#define ENDSTOP_PIN 2    // Define endstop pin
#define STEPS_PER_MM 200 // steps per mm
#define MAX_FEED 10000   // Maximum feed rate in mm/min
#define NORMAL_SPEED 30  // Normal speed in RPM

// Create the motor shield object
Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_StepperMotor *pipetteMotor = AFMS.getStepper(200, 1);
ezButton endstop(ENDSTOP_PIN);

// State variables
bool isHomed = false;
String serialCommand = "";

void setup()
{
  Serial.begin(115200);
  endstop.setDebounceTime(50); // 50ms debounce for endstop

  if (!AFMS.begin())
  {
    Serial.println("Could not find Motor Shield. Check wiring.");
    while (1)
      ;
  }

  pipetteMotor->setSpeed(NORMAL_SPEED);
  Serial.println("OT2 Pipette Driver Ready");
}

void loop()
{
  endstop.loop(); // Update endstop state

  // Handle serial commands
  while (Serial.available() > 0)
  {
    char c = Serial.read();
    if (c == '\n')
    {
      processCommand(serialCommand);
      serialCommand = "";
    }
    else
    {
      serialCommand += c;
    }
  }
}

void processCommand(String command)
{
  if (command == "$PH")
  {
    Serial.println("Starting homing sequence");
    homeRoutine();
    Serial.println("Homing complete");
  }
}

void homeRoutine()
{
  pipetteMotor->setSpeed(200);

  // Fast approach
  while (!endstop.isPressed())
  {
    pipetteMotor->step(1000, BACKWARD, SINGLE);
  }

  // Back off
  pipetteMotor->step(50, FORWARD, SINGLE);
  delay(500);

  // Slow final approach
  pipetteMotor->setSpeed(50);
  while (!endstop.isPressed())
  {
    pipetteMotor->step(100, BACKWARD, SINGLE);
  }

  // Move to starting position (0.5mm)
  pipetteMotor->step(STEPS_PER_MM / 2, FORWARD, SINGLE);

  pipetteMotor->setSpeed(NORMAL_SPEED);
  isHomed = true;
}

void moveRelative(int steps)
{
  if (!isHomed)
  {
    Serial.println("Error: Pipette not homed");
    return;
  }

  if (steps > 0)
  {
    pipetteMotor->step(steps, FORWARD, SINGLE);
  }
  else
  {
    pipetteMotor->step(-steps, BACKWARD, SINGLE);
  }
}

void moveAbsolute(int position)
{
  if (!isHomed)
  {
    Serial.println("Error: Pipette not homed");
    return;
  }

  int currentPosition = 0;
  while (currentPosition < position)
  {
    pipetteMotor->step(1, FORWARD, SINGLE);
    currentPosition++;
  }

  while (currentPosition > position)
  {
    pipetteMotor->step(1, BACKWARD, SINGLE);
    currentPosition--;
  }
}