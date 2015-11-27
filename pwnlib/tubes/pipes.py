import os
import select
import time

from ..log import getLogger
from ..timeout import Timeout
from .tube import tube

log = getLogger(__name__)

class pipes(tube):

    def __init__(self, input_file, output_file, create_pipes = True, open_file = True, timeout = Timeout.default):
        super(pipes, self).__init__(timeout)

        if open_file:
            self.input_file, self.output_file = self._connect(input_file,output_file,create_pipes)
        else:
            self.input_file = input_file
            self.output_file = output_file

    def _connect(self, input_file, output_file, create_pipes = False):
        if create_pipes:
            try:
                os.unlink(input_file)
            except OSError:
                pass
            os.mkfifo(input_file)
            try:
                os.unlink(output_file)
            except OSError:
                pass
            os.mkfifo(output_file)
        input_file = os.open(input_file,os.O_RDONLY|os.O_NONBLOCK)
        output_file = os.open(output_file,os.O_WRONLY)
        return input_file, output_file

    def recv_raw(self,numb):
        if not(self.connected_raw("recv")):
            raise EOFError

        if self.timeout <=0:
            timeout = None
        else:
            timeout = self.timeout

        slist = [self.input_file]
        rfd, wfd, xfd = select.select(slist, [], slist, timeout)
        if len(xfd) > 0:
            raise EOFError
        elif len(rfd) > 0:
            data = os.read(self.input_file,numb)
            if data == "":
                raise EOFError
            else:
                return data
        else: #timeout
            return ""

    def send_raw(self, data):
        if not(self.connected_raw("send")):
            raise EOFError

        if self.timeout <=0:
            timeout = None
        else:
            timeout = self.timeout

        slist = [self.output_file]
        ftime = time.time() + timeout
        ctimeout = ftime - time.time()
        nsent = 0
        while ctimeout > 0 and nsent < len(data):
            rfd, wfd, xfd = select.select([], slist, slist, ctimeout)
            if len(xfd) > 0:
                raise EOFError
            elif len(wfd) > 0:
                nsent += os.write(self.output_file,data[nsent:])
            else: #timeout
                return
            ctimeout = ftime - time.time()

    def settimeout_raw(self, timeout):
        # we do not use any "internal" timeout
        raise NotImplementedError('Not implemented')

    def can_recv_raw(self, timeout):
        if not(self.connected_raw("recv")):
            raise False

        rfd, _, _ = select.select([self.input_file], [], [], timeout)
        return (len(rfd) > 0)

    def connected_raw(self, direction):
        def _is_connected(fd):
            try:
                os.fstat(fd)
            except OSError:
                return False
            return True

        in_connected = _is_connected(self.input_file)
        out_connected = _is_connected(self.output_file)

        if direction == 'any':
            return (in_connected or out_connected)
        elif direction == 'recv':
            return in_connected
        elif direction == 'send':
            return out_connected

    def close(self):
        self.shutdown_raw()

    def fileno(self):
        return self.input_file

    def shutdown_raw(self):
        try:
            os.close(self.input_file)
        except OSError:
            pass
        try:
            os.close(self.output_file)
        except OSError:
            pass
