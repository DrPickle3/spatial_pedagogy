#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define I2C_SDA 4
#define I2C_SCL 5

Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
    Wire.begin(I2C_SDA, I2C_SCL);
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        // Display not found
        for (;;);
    }

    display.clearDisplay();
    display.setTextSize(1);              // Text size
    display.setTextColor(SSD1306_WHITE); // White text
    display.setCursor(0, 0);             // Top-left corner
    display.println("Hello World !");
    display.display();                    // Render it
}

void loop() {
    // Nothing else needed
}
