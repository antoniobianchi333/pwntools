#!/usr/bin/env python

import socket
import os
import signal
import subprocess
import select
import argparse
import hmac
import hashlib
import time

DEFAULT_PORT = 3456
DEFAULT_IP = "127.0.0.1"
DEFAULT_PASSWORD = "password"


class looper_client():

    def __init__(self,port=DEFAULT_PORT,ip=DEFAULT_IP,password=DEFAULT_PASSWORD,sleep_time=0.0):
        self.port = port
        self.ip = ip
        self.password = password
        self.sleep_time = sleep_time

    def invoke(self,code):
        if "\n" in code:
            raise Exception("New lines are not allowed in looper's code")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.ip,self.port))
        except socket.error:
            raise Exception("Cannot connect to looper_server at "+self.ip+":"+str(self.port))

        nounce_len = 32
        nounce = ""
        while len(nounce) < nounce_len:
            nounce += s.recv(nounce_len-len(nounce))

        s.sendall(code)
        s.sendall("\n")
        s.sendall(nounce)
        mac = hmac.new(self.password,code+"\n"+nounce,hashlib.sha256).digest().encode('hex')
        s.sendall("\n")
        s.sendall(mac)
        s.close()
        time.sleep(self.sleep_time)


class looper_server():

    def __init__(self, port=DEFAULT_PORT, ip=DEFAULT_IP, password=DEFAULT_PASSWORD):
        self.ip = ip
        self.port = port
        self.password = password
        if self.password == DEFAULT_PASSWORD:
            print "WARNING:", "using default password allows arbitrary code execution to anyone that can connect to ", \
                    self.ip+":"+str(self.port)

        self.main_loop()

    def main_loop(self):
        sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sk.bind((self.ip, self.port))
        sk.listen(1)
        self.socket = sk
        
        first = True
        self.process = None
        try:
            while True:
                print "*** waiting from new connections on:",self.ip,str(self.port)
                conn,addr,nounce = self.wait_socket_and_process()
                print "*** new connection from",addr
                if first:
                    first = False
                    self.reset_terminal()

                full_data = ""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    full_data += data

                cmd = self.parse_and_verify_cmd(full_data,nounce)
                if cmd == None:
                    print "* invalid command received"
                    continue
                else:
                    print "* executing command",cmd
                self.process = subprocess.Popen(cmd,preexec_fn=self.become_tty_fg,shell=True)

        except KeyboardInterrupt:
            print "*** terminating..."
            if (self.process != None and self.process.poll() == None):
                os.killpg(process.pid,9)
                self.process.poll()
                self.reset_terminal()
            self.become_tty_fg(False)


    #as in: https://gist.github.com/thepaul/1206753
    def become_tty_fg(self,child=True):
        os.setpgrp()
        hdlr = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        tty = os.open('/dev/tty', os.O_RDWR)
        os.tcsetpgrp(tty, os.getpgrp())
        if child:
            signal.signal(signal.SIGTTOU, hdlr)

    def reset_terminal(self):
        subprocess.Popen("reset",shell=True).communicate()

    def wait_socket_and_process(self):
        while True:
            rr,_,_ = select.select([self.socket],[],[],0.1)
            if len(rr)>0:
                conn, addr = rr[0].accept()
                if self.process != None:
                    os.killpg(self.process.pid,9)
                    self.process.poll()
                    self.become_tty_fg(False)
                    subprocess.Popen("reset",shell=True).communicate()
                    print "* subprocess killed"
                nounce = os.urandom(16).encode('hex')
                conn.sendall(nounce)
                return conn,addr,nounce
            elif (self.process != None and self.process.poll() != None):
                self.become_tty_fg(False)
                self.process = None
                print "* subprocess terminated"


    def parse_and_verify_cmd(self,tstr,nounce):
        def constant_time_compare(str1, str2):
            #as in django source code
            if len(str1) != len(str2):
                return False
            result = 0
            for c1, c2 in zip(str1, str2):
                result |= ord(c1) ^ ord(c2)
            return result == 0

        cmd,remote_nounce,remote_mac = tstr.split("\n")
        local_mac = hmac.new(self.password,cmd+"\n"+nounce,hashlib.sha256).digest().encode('hex')
        if constant_time_compare(remote_mac,local_mac) and nounce == remote_nounce:
            return cmd
        else:
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Looper server process to be used in conjunction with looper client.')
    parser.add_argument('--ip',type=str,help='ip on which the looper will listen',default=DEFAULT_IP)
    parser.add_argument('--port',type=int,help='port on which the looper will listen',default=DEFAULT_PORT)
    parser.add_argument('--password',type=str,help='password used to authenticate a Looper instance',default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    ls = looper_server(args.port,args.ip,args.password)


'''
in one shell:
from pwn import *
r = tty_process("/tmp/tty1")
looper_client().invoke("../ctf-tools/bin/gdb  -x tmp/commands.txt --args python tmp/test_buffering.py")
r.recv()

tmp/commands.txt content:
tty /tmp/tty1
r

in other shell:
python -c "from pwn import *; looper_server()"
'''
