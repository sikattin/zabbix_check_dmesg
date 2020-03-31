#!/usr/bin/python
"""check_dmesg.py

Zabbix UserParameter Script

Send kernel messages of err level or more on boot to Zabbix Server

Requires:
  python >= 2.7.0
  util-linux >= 2.21
  zabbix-sender

ENVIROMENT VARIABLES:
  ZBXSENDER_EXEC: zabbix_sender executable path
  DMESG_EXEC: dmesg executable path
"""
import os
import sys
import socket
from subprocess import check_call, \
                       CalledProcessError


ALREADY_EXECUTED = "/dev/shm/{0}.ae".format(os.path.splitext(os.path.basename(__file__))[0])
TMPFILE = "/tmp/{0}.tmp".format(os.path.basename(__file__))
ZBX_ITEMKEY = 'sys.kernel.dmesg'
ZBXAGENT_CONF = '/etc/zabbix/zabbix_agentd.conf'
ZBXSENDER_EXEC = '/usr/bin/zabbix_sender'

class ZabbixSender(object):

    def __init__(self,
                 executable,
                 zabbix_server,
                 port=10051,
                 host=socket.gethostname(),
                 zbxagent_conf=None
    ):
        """constructor
        
        Args:
            executable (str): zabbix_sender executable absolute path
            zabbix_server (str): Zabbix Server Host/IP
            port (int, optional): Zabbix Server Listening Port. Defaults to 10051.
            host (str, optional): host name the item belongs to.
                                    Defaults to socket.gethostname().
            zbxagent_conf (str, optional):
                Zabbix Agent config file path.
                if specified, `zabbix_server` and `port` arguments be ignored.
                Defaults to None.
        """
        if zbxagent_conf is not None:
            self.is_useconf = True
        else:
            self.is_useconf = False
        
        self.executable = executable
        self.zabbix_server = zabbix_server
        self.port = str(port)
        self.host = host
        self.zbxagent_conf = zbxagent_conf

    @staticmethod
    def which_zbxsender():
        """Checking for zabbix_sender installed
        
        Returns:
            [str]: Absolute path of executable if installed, otherwise string of length 0.
        """
        from subprocess import check_output
        result = ""
        try:
            result = check_output(["which", "zabbix_sender"])
        except CalledProcessError as e:
            sys.stderr.write("Zabbix-sender not installed.\n")
            sys.exit(e.returncode)
        return result.decode().rstrip()

    def send_values(self, file):
        """Send item values to Zabbix Server by input file
        
        Args:
            file (str): input file path. See also zabbix_sender(1)
        
        Returns:
            [str]: command output if returncode not 0, otherwise string of length 0
        """
        res = ""
        if self.is_useconf:
            cmd = [
                "{0}".format(self.executable),
                "-c",
                "{0}".format(self.zbxagent_conf),
                "-s",
                "{0}".format(self.host),
                "-i",
                "{0}".format(file)
            ]
        else:
            cmd = [
                "{0}".format(self.executable),
                "-z",
                "{0}".format(self.zabbix_server),
                "-p",
                "{0}".format(self.port),
                "-s",
                "{0}".format(self.host),
                "-i",
                "{0}".format(file)
            ]
        try:
            res = check_call(cmd)
        except CalledProcessError as e:
            sys.stderr.write("zabbix_sender execution has failed with {0} exit code\n"
                .format(e.returncode)
            )
            raise e
        return res


def exit():
    os.remove(TMPFILE)
    with open(ALREADY_EXECUTED, 'w') as f:
        pass
    
if __name__ == "__main__":

    def init():
        ver = sys.version_info
        global zbxsender_exec
        global dmesg_exec
        global hostname
        # zabbix_sender executable path
        # less thant python 2.6, force to use constant variable
        zbxsender_exec = os.getenv('ZBXSENDER_EXEC')
        if ver[0] == 2 and ver[1] <= 6 and zbxsender_exec is None:
            print("Under Python 2.6")
            zbxsender_exec = ZBXSENDER_EXEC
        else:
            print("Python 2.7 later")
            zbxsender_exec = ZabbixSender.which_zbxsender()
        
        dmesg_exec = os.getenv('DMESG_EXEC')
        if dmesg_exec is None:
            dmesg_exec = 'dmesg'
        hostname = socket.gethostname()


    if os.path.exists(ALREADY_EXECUTED):
        print("has already exexuted.")
        sys.exit(0)

    zbxsender_exec = ""
    dmesg_exec = ""
    hostname = ""
    init()
    zbxsender = ZabbixSender(zbxsender_exec,
                             "Zabbix-Server",
                             zbxagent_conf=ZBXAGENT_CONF)

    # open ring buffer and write logs to temporaly file.
    tmpf = open(TMPFILE, 'w')
    with os.popen("{0} -x -T --level emerg,alert,crit,err".format(dmesg_exec)) as f:
        for line in f:
            tmpf.write("{0} {1} \"{2}\"\n".format(hostname, ZBX_ITEMKEY, line.rstrip()))
        tmpf.close()

    # Send values to zabbix server.
    res = zbxsender.send_values(TMPFILE)
    if res == 0:
        print(res)
    else:
        sys.stderr.write("Not sent.\n")
        sys.exit(1)
    
    exit()
