from math import atan, atan2, pi, degrees

pi_by_8 = pi/8
two_pi = 2*pi

def angle(x,y):
    a = degrees(atan2(y,x))
    return a if a >= 0 else 360+a

def sector(x,y):
    a = atan2(y,x)
    if a < 0:
        a = two_pi+a
    return round(a/pi_by_8)

def t(x,y):
    print(x, y, sector(x,y))
    
t(1,0)
t(1,0.1)
t(1,0.5)
t(1,0.9)
t(1,1)
t(1,1.5)
t(0.1,1)

t(0,1)
t(-0.1,1)
t(-0.9,1)
t(-1,1)
t(-1.1,1)
t(-1,0.9)
t(-1,0.1)
t(-1,0)

t(-1,-1)
t(0,-1)
t(0.1,-1)
t(0.9,-1)
t(1,-0.9)
t(1,-0.1)
