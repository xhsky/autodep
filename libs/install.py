#!/usr/bin/env python
# coding:utf8
# sky

from libs import client

class soft(object):
    def  __init__(self, ip, port):
        self.ssh=client.Client()
        self.ip=ip
        self.port=port

    """
    def tar_install(self, soft_name, ip, port, install_dir):
        remote_file=f"/tmp/{soft_name.split('/')[-1]}"
        self.obj.scp(ip, port, "root", soft_name, remote_file)
        command=f"tar -xf {remote_file} -C {install_dir} && echo 0"
        status=self.obj.exec(ip, port, command)
        return status
    """

    def control(self, soft_name, action, weight, soft_file, json_info):
        py_file=f"./bin/{soft_name}.py"
        install_pkg_name=soft_file.split("/")[-1]

        code_dir="/opt/python3/code"

        if action=="install":
            self.ssh.scp(self.ip, self.port, "root", py_file, f"{code_dir}/{soft_name}.py")
            self.ssh.scp(self.ip, self.port, "root", soft_file, f"/tmp/{install_pkg_name}")

        command=f"/opt/python3/bin/python3 {code_dir}/{soft_name}.py {action} {weight} /tmp/{install_pkg_name} {json_info}"
        status=self.ssh.exec(self.ip, self.port, command)
        return status

if __name__ == "__main__":
    pass


