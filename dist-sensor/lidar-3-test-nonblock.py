from machine import I2C, Pin
from opt3101 import OPT3101, BRIGHTNESS_ADAPTIVE
import time

i2c = I2C(0, sda=Pin(5), scl=Pin(6))
sensor = OPT3101( i2c )

#sensor.set_frame_timing(256)
sensor.set_frame_timing(64)
sensor.set_channel(0)
sensor.set_brightness( BRIGHTNESS_ADAPTIVE )
sensor.start_sample()

amplitudes = list([0,0,0])
distances  = list([0,0,0]) # in mm

# Main program loop
print( '           :     TX0 :     TX1 :     TX2' )
print( '-'*40 )
while True:
    if sensor.is_sample_done():
        sensor.read_output_regs() # Read data from board
        # stored into array
        amplitudes[sensor.channel_used] = sensor.amplitude
        distances[sensor.channel_used] = sensor.distance # in mm
        # Display data (or perform processing on the data)
        if sensor.channel_used == 2: # if we did read the 3 sensors
            print( 'Amplitudes : %7i : %7i : %7i' % (amplitudes[0], amplitudes[1], amplitudes[2]) )
            print( 'Distances : %7i : %7i : %7i' % (distances[0], distances[1], distances[2]) )
            print( '-'*40 )
        # loop to next channel + acquire
        sensor.next_channel()
        sensor.start_sample()
        time.sleep(0.2)
