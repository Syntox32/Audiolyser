# Audiolyser #

Audiolyser is a repository for keeping track of my adventures creating an audio visualizer with 32 RGB LEDs connected to my RaspberryPi

[Here you can see it in action!](http://s1.webmshare.com/1L6Rz.webm)

# Example Usage #

If you're brave enough to tackle all the errors that will occur, you can try run this:  
```
(Windows/Client) python ledclient.py -i <rpi-ip> -p <port> -s <song-path> [--force-cache]
```
```
(RPi/Server)     sudo python ledserver.py -i <rpi-ip> -p <port> [--channel <primary-channel>]
```
Currently the client code has only been tested on windows, but should in theory run on any unix system with little to no modifications.  
The songs also needs to in the .WAV format, mp3 support is still not implemented..

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
Raspberry Pi: 
* spidev  
* numpy  
* alsaaudio[temp]  

Windows:  
* numpy  
* pyaudio  
```
