import sys

sys.stdout.write("HI!\n")
sys.stdout.flush()
while True:
    c =  sys.stdin.readline()
    sys.stdout.write(repr(c) + " " + c.encode('hex') + "\n")
    sys.stdout.flush()



