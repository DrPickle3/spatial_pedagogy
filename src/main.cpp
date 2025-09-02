#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "DW1000.h"
#include "DW1000Ranging.h"

// OLED CONFIG
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define I2C_SDA 4 // PINS
#define I2C_SCL 5
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET); // equivalent of console with console.log() / clear()/ etc.

// DW1000 SPI pins
#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23

#define UWB_RST 27
#define UWB_IRQ 34
#define UWB_SS 21

// Comment next line if pushing code for a tag
#define PUSHING_ANCHOR_CODE

#define ANCHOR_ID "86:17:5B:D5:A9:9A:E2:9C" // Default manufacturer ID
#define TAG_ID "7D:00:22:EA:82:60:3B:9B"    // Random ID different from the anchor one

long runtime = 0;

void newRange() // Runs everytime a new range measurement is being registered between the anchor and the tag.
{
  DW1000Device *dev = DW1000Ranging.getDistantDevice(); // Fetches the anchor
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 20);

  if (dev != nullptr) // Anchor exists
  {
    float range = dev->getRange();
    display.print("Range: ");
    display.print(range, 2);
    display.println(" m");
  }
  else
  {
    display.println("No Anchor");
  }

  display.display();
}

void newBlink(DW1000Device *device) //Tags notifying every anchor that they are connected
{
  display.println("New tag connected! :)");
  display.display();
}

void newDevice(DW1000Device *device) {} //When tags are ready to be raged they will trigger this function
void newInactiveDevice(DW1000Device *device) {} //Triggers when a device become inactive

void setup()
{
  Wire.begin(I2C_SDA, I2C_SCL); //Starts both OLED pins
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);  //Starts he OLED
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);

#ifdef PUSHING_ANCHOR_CODE
  display.println("Anchor initializing...");
#else
  display.println("Tag initializing...");
#endif

  display.display();  //Put on display

  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);                     // Starts the range connection and data
  DW1000Ranging.initCommunication(UWB_RST, UWB_SS, UWB_IRQ);  // exchange

#ifdef PUSHING_ANCHOR_CODE
  DW1000Ranging.attachBlinkDevice(newBlink);
#else
  DW1000Ranging.attachNewRange(newRange);
#endif

  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(newInactiveDevice);

#ifdef PUSHING_ANCHOR_CODE
  DW1000Ranging.startAsAnchor(ANCHOR_ID, DW1000.MODE_SHORTDATA_FAST_ACCURACY, false);
  display.clearDisplay();
  display.println("ANCHOR : ");
  display.println(ANCHOR_ID);
  display.display();
#else
  DW1000Ranging.startAsTag(TAG_ID, DW1000.MODE_SHORTDATA_FAST_ACCURACY);
#endif
}

void loop()
{
  DW1000Ranging.loop();
}