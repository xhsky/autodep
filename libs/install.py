#!/usr/bin/env python
# coding:utf8
# sky

from libs import client
from libs.common import Logger
from libs.env import log_file, log_file_level, remote_python_exec
import json

class soft(object):
    def  __init__(self, ip, port):
        self.ssh=client.Client()
        self.ip=ip
        self.port=port
        self.log=Logger({"file": log_file_level}, logger_name=ip, log_file=log_file)

    def control(self, py_file, action, args_dict):
        command=f"{remote_python_exec} {py_file} {action} '{json.dumps(args_dict)}'"
        self.log.logger.debug(f"{action=}: {command=}")
        status=self.ssh.exec(self.ip, self.port, command)
        return status
    
    def install(self, trans_files_dict, args_dict):
        for trans_file in trans_files_dict:
            src, dst=trans_files_dict[trans_file]
            self.log.logger.debug(f"传输文件: {trans_file}, {src=}, {dst=}")
            self.ssh.scp(self.ip, self.port, "root", src, dst)
        py_file=trans_files_dict["py_file"][1]
        args_dict["pkg_file"]=trans_files_dict["pkg_file"][1]
        status=self.control(py_file, "install", args_dict)
        return status

    def start(self, py_file, args_dict):
        status=self.control(py_file, "start", args_dict)
        return status

if __name__ == "__main__":
    pass


