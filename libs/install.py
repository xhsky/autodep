#!/usr/bin/env python
# coding:utf8
# sky

from libs import client
from libs.common import Logger
from libs.env import log_file
import json

class soft(object):
    def  __init__(self, ip, port):
        self.ssh=client.Client()
        self.ip=ip
        self.port=port
        self.log=Logger({"file": "debug"}, logger_name="soft", log_file=log_file)

    #def control(self, softname, action, weight, soft_file, json_info):
    def control(self, softname, action, args_dict):
        #command=f"{args_dict['remote_python_exec']} {code_dir}/{soft_name}.py {action} {weight} /tmp/{install_pkg_name} {json_info}"
        command=f"{args_dict['remote_python_exec']}  {args_dict['trans_files']['py_file'][1]} {action} '{json.dumps(args_dict)}'"
        self.log.logger.debug(f"{action}: {command=}")
        status=self.ssh.exec(self.ip, self.port, command)
        return status
    
    def install(self, softname, args_dict):
        for trans_file in args_dict["trans_files"]:
            src, dst=args_dict["trans_files"][trans_file]
            self.log.logger.debug(f"传输文件: {trans_file}, {src=}, {dst=}")
            self.ssh.scp(self.ip, self.port, "root", src, dst)
        self.control(softname, "install", args_dict)

    def start(self, softname, args_dict):
        self.control(softname, "start", args_dict)

if __name__ == "__main__":
    pass


