Divoom Pixoo client for Python3
===============================

This small python script provides a way to communicate with a Divoom Pixoo
over Bluetooth. 

This script provides a class able to manage a Pixoo, but you need to create your
own code to make it work.

Dependencies
------------

Use a third-party software to bind your computer with your pixoo (BlueZ + blueman-applet for instance).
Then you may use this python class to manage your Pixoo.

How to use this class
---------------------

This class provides many methods to connect and manage a Pixoo device.

* connect(): creates a connection with the device and keeps it open while the script is active
* draw_pic(): draws a picture (resized to 16x16 pixels) from a PNG file
* draw_anim(): displays an animation on the Pixoo based on a GIF file (16x16 pixels)
* set_system_brightness: set the global brightness to a specific level (0-100)


