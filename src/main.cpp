#include <SPI.h>
#include "DW1000Ranging.h"

#include <WiFi.h>
#include "esp_wpa2.h"

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <vector>
#include "secrets.h"

char ANCHOR_ADD[] = "A3:AA:5B:D5:A9:9A:E2:9C";
char TAG_ADDR[] = "7D:00:22:EA:82:60:3B:9B";

// SAVED ANCHOR CALIBRATIONS (Not good anymore)
// A1 = 16446 (+10) Accurate
// A2 = 16511 (+75) Not that good
// A3 = 16456 (+20) Not much better
// A4 = 16406 (-30) Almost perfect
// REF TAG = 16436

/*
* Distance from Tag to Anchor 1 : 3.449
* True Distance Tag/Anchor1 : 2.8702
* 
* Distance measured from Tag to Anchor 4 : 3.045
* True Distance Tag/Anchor4 : 2.5908
* 
* Distance measured from Anchor 1 to Anchor 4 : 2.370
* True Distance Anchor1/Anchor4 : 1.7018
* 
* 
* ------------- Corrections --------------
* Tag     : 39
* Anchor1 : 85
* Anchor4 : 58
* Anchor2 : 98
* Anchor3 : 89
* 
* Distance from Tag to Anchor 1 : 1.905
* True Distance Tag/Anchor1 : 1.901
* 
* Distance measured from Tag to Anchor 4 : 1.8288
* True Distance Tag/Anchor4 : 1.842
* 
* Distance measured from Anchor 1 to Anchor 4 : 2.370
* True Distance Anchor1/Anchor4 : 1.7018
* 
*/

#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23

#define UWB_RST 27 // reset pin
#define UWB_IRQ 34 // irq pin
#define UWB_SS 21  // spi select pin

#define I2C_SDA 4
#define I2C_SCL 5

#define RANGE_HISTORY 5

// Comment to push tag code
// #define PUSHING_ANCHOR_CODE

Adafruit_SSD1306 display(128, 64, &Wire, -1);

#ifndef PUSHING_ANCHOR_CODE

const char *ssid = "CamPhone"; // works even on eduroam
WiFiClient client;
String all_json = "";

const char *serverIP = "10.172.206.138";
const uint16_t serverPort = 5000;

float median_filter(float *arr, int size)
{
    std::vector<float> temp;
    for (int i = 0; i < size; i++)
        if (arr[i] > 0.01) // ignore zeros
            temp.push_back(arr[i]);

    if (temp.empty()) return 0.0;

    std::sort(temp.begin(), temp.end());
    return temp[temp.size() / 2];
}

struct Link
{
  uint16_t anchor_addr;
  float range_history[RANGE_HISTORY];
  int history_index;
  float dbm;
  struct Link *next;
};

struct Link *uwb_data;

// Data Link

struct Link *init_link()
{
  struct Link *p = (struct Link *)malloc(sizeof(struct Link));
  p->next = NULL;
  p->anchor_addr = 0;
  for (int i = 0; i < RANGE_HISTORY; i++)
  {
    p->range_history[i] = 0.0;
  }
  p->history_index = 0;

  return p;
}

void add_link(struct Link *p, uint16_t addr)
{
  struct Link *temp = p;
  // Find struct Link end
  while (temp->next != NULL)
  {
    temp = temp->next;
  }

  Serial.println("add_link:find struct Link end");
  // Create a anchor
  struct Link *a = (struct Link *)malloc(sizeof(struct Link));
  a->anchor_addr = addr;
  for (int i = 0; i < RANGE_HISTORY; i++)
  {
    a->range_history[i] = 0.0;
  }
  a->history_index = 0;
  a->dbm = 0.0;
  a->next = NULL;

  // Add anchor to end of struct Link
  temp->next = a;

  return;
}

struct Link *find_link(struct Link *p, uint16_t addr)
{
  if (addr == 0)
  {
    Serial.println("find_link:Input addr is 0");
    return NULL;
  }

  if (p->next == NULL)
  {
    Serial.println("find_link:Link is empty");
    return NULL;
  }

  struct Link *temp = p;
  // Find target struct Link or struct Link end
  while (temp->next != NULL)
  {
    temp = temp->next;
    if (temp->anchor_addr == addr)
    {
      // Serial.println("find_link:Find addr");
      return temp;
    }
  }

  Serial.println("find_link:Can't find addr");
  return NULL;
}

void fresh_link(struct Link *p, uint16_t addr, float range, float dbm)  
{
    if (range < 0.1 || range > 10.0) return; // Ignore negative values and above 10 meters

    struct Link *temp = find_link(p, addr);
    if (temp != NULL)
    {
        // Insert new value in circular buffer
        temp->range_history[temp->history_index] = range;
        temp->history_index = (temp->history_index + 1) % RANGE_HISTORY;

        // Save RX power
        temp->dbm = dbm;
    }
    else
    {
        Serial.println("fresh_link:Fresh fail");
    }
}

void print_link(struct Link *p)
{
  struct Link *temp = p;

  while (temp->next != NULL)
  {
    temp = temp->next;
    // Serial.println("Dev %d:%d m", temp->next->anchor_addr, temp->next->range);
    Serial.println(temp->anchor_addr, HEX);
    Serial.println(median_filter(temp->range_history, RANGE_HISTORY));
    Serial.println(temp->dbm);
  }

  return;
}

void delete_link(struct Link *p, uint16_t addr)
{
  if (addr == 0)
    return;

  struct Link *temp = p;
  while (temp->next != NULL)
  {
    if (temp->next->anchor_addr == addr)
    {
      struct Link *del = temp->next;
      temp->next = del->next;
      free(del);
      return;
    }
    temp = temp->next;
  }
  return;
}

void make_link_json(struct Link *p, String *s)
{
  *s = "{\"links\":[";
  struct Link *temp = p;

  while (temp->next != NULL)
  {
    temp = temp->next;
    char link_json[50];
    sprintf(link_json, "{\"A\":\"%X\",\"R\":\"%.3f\"}", temp->anchor_addr, median_filter(temp->range_history, RANGE_HISTORY));
    *s += link_json;
    if (temp->next != NULL)
    {
      *s += ",";
    }
  }
  *s += "]}";
}
#endif

void newRange()
{
  Serial.print("from: ");
  Serial.print(DW1000Ranging.getDistantDevice()->getShortAddress(), HEX);
  Serial.print("\t Range: ");
  Serial.print(DW1000Ranging.getDistantDevice()->getRange());
  Serial.print(" m");
  Serial.print("\t RX power: ");
  Serial.print(DW1000Ranging.getDistantDevice()->getRXPower());
  Serial.println(" dBm");

#ifndef PUSHING_ANCHOR_CODE
  fresh_link(uwb_data, DW1000Ranging.getDistantDevice()->getShortAddress(), DW1000Ranging.getDistantDevice()->getRange(), DW1000Ranging.getDistantDevice()->getRXPower());
#endif
}

void newBlink(DW1000Device *device)
{
#ifdef PUSHING_ANCHOR_CODE
  Serial.print("blink; 1 device added ! -> ");
  Serial.print(" short:");
  Serial.println(device->getShortAddress(), HEX);
#endif
}

void newDevice(DW1000Device *device)
{
  Serial.print("ranging init; 1 device added ! -> ");
  Serial.print(" short:");
  Serial.println(device->getShortAddress(), HEX);
#ifndef PUSHING_ANCHOR_CODE
  add_link(uwb_data, device->getShortAddress());
#endif
}

void inactiveDevice(DW1000Device *device)
{
  Serial.print("delete inactive device: ");
  Serial.println(device->getShortAddress(), HEX);

#ifndef PUSHING_ANCHOR_CODE
  delete_link(uwb_data, device->getShortAddress());
#endif
}

// SSD1306

void logoshow(void)
{
  display.clearDisplay();

  display.setTextSize(2);              // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 0);             // Start at top-left corner
  display.println(F("Makerfabs"));

  display.setTextSize(1);
  display.setCursor(0, 20);
#ifdef PUSHING_ANCHOR_CODE
  display.println(F("ANCHOR"));
  display.println(ANCHOR_ADD);
#else
  display.println(F("TAG"));
#endif
  display.display();
  delay(2000);
}

#ifndef PUSHING_ANCHOR_CODE
int count_links(struct Link *p)
{
  int count = 0;
  struct Link *temp = p;

  while (temp->next != NULL)
  {
    temp = temp->next;
    count++;
  }

  return count;
}

void display_uwb(struct Link *p)
{
    struct Link *temp = p;
    int row = 0;

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);

    if (temp->next == NULL)
    {
        display.setTextSize(2);
        display.setCursor(0, 0);
        display.println("No Anchor");
        display.display();
        return;
    }

    while (temp->next != NULL)
    {
        temp = temp->next;

        float filtered_range = median_filter(temp->range_history, RANGE_HISTORY);

        char c[20];
        sprintf(c, "%.2f m", filtered_range);

        display.setTextSize(1);
        display.setCursor(0, row++ * 16);

        char buf[5];
        sprintf(buf, "%04X", temp->anchor_addr); // hex address
        display.print(buf);
        display.print(" : ");
        display.println(c);
    }

    display.display();
}

void send_tcp(String *msg_json)
{
  if (client.connected())
  {
    client.print(*msg_json);
  }
}
#endif

void setup()
{
  Serial.begin(115200);

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(1000);
  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
  { // Address 0x3C for 128x32
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ; // Don't proceed, loop forever
  }
  display.clearDisplay();

  logoshow();

  DW1000.setAntennaDelay(16436 + 39);

#ifndef PUSHING_ANCHOR_CODE
  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);

  WiFi.begin(ssid, EDUROAM_PASS);

  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  if (client.connect(serverIP, serverPort))
  {
    Serial.println("Connected to server!");
  }
  else
  {
    Serial.println("Connection failed");
  }
#endif

  // init the configuration
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
  DW1000Ranging.initCommunication(UWB_RST, UWB_SS, UWB_IRQ); // Reset, CS, IRQ pin
  // define the sketch as anchor. It will be great to dynamically change the type of module
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachBlinkDevice(newBlink);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);
  // Enable the filter to smooth the distance
  // DW1000Ranging.useRangeFilter(true);

#ifdef PUSHING_ANCHOR_CODE
  DW1000Ranging.startAsAnchor(ANCHOR_ADD, DW1000.MODE_LONGDATA_RANGE_LOWPOWER, false);
#else
  DW1000Ranging.startAsTag(TAG_ADDR, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);
  uwb_data = init_link();
#endif
}

long int runtime = 0;

void loop()
{
  DW1000Ranging.loop();
#ifndef PUSHING_ANCHOR_CODE
  if ((millis() - runtime) > 100)
  {
    make_link_json(uwb_data, &all_json);
    send_tcp(&all_json);
    display_uwb(uwb_data);
    runtime = millis();
  }
#endif
}