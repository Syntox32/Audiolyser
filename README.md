# ProjectLED #

ProjectLED is a repository for keeping track of my adventures creating an audio visualizer with 32 RGB LEDs connected to my RaspberryPi

# How to start it currently #

INSUFFICIENT DATA FOR MEANINGFUL ANSWER

# Wiring #
Your LED strip might look a bit different, mine had 6 cables.  
Since no documentation followed with the strip(and I had little success finding anything on the internet), I just tried my way through getting it to work.  
Since every strip I found documentation for only had 4 cables I connected my two power cables into one, and then proceeded to do the same with the ground cables, it has yet to blow up.
```
::text
WS2801 RGB 24-bit LED Lightstrip

Data is sent in an array using SPI:
[array]->RGBRGBRGB...

Red   : 5V+
Black : GND

Green : 5V+
Red   : CLK  -> SCLK
Blue  : DATA -> MOSI
Black : GND

    /-------[V+  RED    5V+]---+--------------------------------\
   /  /-----[GND BLACK  GND]---|---+------------------------\   |
  /  /                         |   |                        |   |
---------+--[V+  GREEN  5V+]---/   |               +-----+  |   |
 WS2801  |--[CI  RED    CLK]-------|--[SCLK PORT]--| RPi |  |   |
         |--[DI  BLUE  DATA]-------|--[MOSI PORT]--|     |--+---+--[2A 5V]
---------+--[GND BLACK  GND]-------/               +-----+       [WALLPOWER]
```

# Requirements #
Currently the project is using **Python 2.7**    
  You also need the current libraries to be installed:  
```
Server(Raspberry Pi):  
 1. spidev
 2. numpy
 3. alsaaudio[temp]  

Client(Your computer):  
 1. numpy
 2. pyaudio
```

d:\python27\python.exe music-test.py -i 192.168.1.108 -p 1337 -s downtheroad.wav

sudo python ledshow.py -i 192.168.1.108 -p 1337 -s downtheroad.wav