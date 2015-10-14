import sys

sys.stdout.write("HI!~")
#sys.stdout.flush()
while True:
    c =  sys.stdin.read(1)
    sys.stdout.write(repr(c) + " " + c.encode('hex') + "~")
    #sys.stdout.flush()



