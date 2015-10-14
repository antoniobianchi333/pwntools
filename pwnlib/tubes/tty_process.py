import os
import pty
import tty

from ..log import getLogger
from ..timeout import Timeout
from inout_file import inout_file

log = getLogger(__name__)

class tty_process(inout_file):

    def __init__(self, tty_name = None, timeout = Timeout.default):
        self.master, self.slave = self._create_tty()
        self.tty_slave_original_fname = self._fd_to_filename(self.slave)
        if tty_name != None:
            self._create_tty_link(self.tty_slave_original_fname,tty_name)
            self.tty_slave_fname = tty_name
        else:
            self.tty_slave_fname = self.tty_slave_original_fname
        super(tty_process, self).__init__(self.master,self.master,False,False,timeout)

    def _fd_to_filename(self,fd):
        return os.path.abspath(os.readlink(os.path.join("/proc/self/fd/",str(fd))))

    def _create_tty(self):
        m,s = pty.openpty()
        tty.setraw(m)
        tty.setraw(s)
        return m,s

    def _create_tty_link(self,original_name,tty_name):
        try:
            os.unlink(tty_name)
        except OSError:
            pass
        os.symlink(original_name,tty_name)

    def close(self):
        self.shutdown_raw()

    def shutdown_raw(self):
        try:
            os.close(self.master)
        except OSError:
            pass
        try:
            os.close(self.slave)
        except OSError:
            pass     
