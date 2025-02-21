# Raspberry Pi Coffee Roaster
[Source](https://coffeehacks.blogspot.com/2016/02/electric-lights-and-fire-elf-raspberry.html)

### GPIO layout:
![RaspberryPi](images/GPIO-Pinout-Diagram-2.png)

### Sensor:
Used [MAX31855 Thermocouple](https://learn.adafruit.com/thermocouple/python-circuitpython) for temperature measurement.

| Pin | Sensor |
| :----: | :------: |
| 1 | Vin |
| 9 | Gnd |
| 21 | DO |
| 29 | CS |
| 23 | CLK |

### Relay:

Used [SSR-25DD](https://www.amazon.com/SSR-25DD-Solid-State-Relay-Output/dp/B08FQWB8HJ) solid state relay with an NPN transistor and a resistor to switch the 5V.

| Pin | Relay |
| :----: | :------: |
| 2 | + |
| 11 | P |

The - of the relay goes to the N side of the NPN transistor.
Pin 11 goes to the P side of the NPN transistor.
The other N side goes to GND (I used Pin 9) with the resistor inline.

Diagram:

![ELF Wiring](images/Roaster%20Schematic.png)
