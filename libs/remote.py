#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-26 11:21:38
# sky

import paramiko
import os, json
from libs.common import Logger
from libs.env import log_file, log_file_level, remote_python_exec

log=Logger({"file": log_file_level}, logger_name="remote", log_file=log_file)

class soft(object):
    def  __init__(self, ip, port, ssh):
        self.ip=ip
        self.port=port
        self.ssh=ssh

    def init(self, py_file, init_args):
        command=f"{remote_python_exec} {py_file} '{json.dumps(init_args)}'"
        log.logger.debug(f"init: {command}")
        status=self.ssh.exec(self.ip, self.port, command)
        return status

    def control(self, py_file, action, args_dict):
        command=f"{remote_python_exec} {py_file} {action} '{json.dumps(args_dict)}'"
        log.logger.debug(f"{action=}: {command}")
        status=self.ssh.exec(self.ip, self.port, command)
        return status
    
    def install(self, py_file, args_dict):
        status=self.control(py_file, "install", args_dict)
        return status

    def start(self, py_file, args_dict):
        status=self.control(py_file, "start", args_dict)
        return status

class ssh(object):
    def __init__(self):
        self.ssh=paramiko.SSHClient()
        #self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self.key_dir="/root/.ssh"
        self.key_file=f"{self.key_dir}/id_rsa"
        self.key_pub_file=f"{self.key_dir}/id_rsa.pub"

    def password_conn(self, ip, port, password, user='root'): 
        try:
            self.ssh.connect(ip, port=port, username=user, password=password, timeout=1)     # 正常连接
            status=0
            msg="正常连接"
        except paramiko.ssh_exception.NoValidConnectionsError as e:               # 端口无法连接
            status=1
            msg="端口无法连接"
        except paramiko.ssh_exception.AuthenticationException as e:               # 密码错误
            status=2
            msg="密码错误"
        except Exception as e:                                                    # 未知错误
            status=3
            msg=f"未知错误, 无法连接({e})"
        #self.ssh.close()
        return status, msg

    def gen_keys(self):
        """生成公私钥对"""

        if not os.path.exists(self.key_dir):
            os.mkdir(self.key_dir)
            os.chmod(self.key_dir, 0o700)

        if os.path.exists(self.key_file) and os.path.exists(self.key_pub_file):
            return 0
        else:
            # 生成私钥文件
            key=paramiko.rsakey.RSAKey.generate(2048)
            key.write_private_key_file(self.key_file)
            # 生成公钥文件
            key_pub=key.get_base64()
            key_pub_and_sign="%s%s" % (" ".join(["ssh-rsa", key_pub]), "\n")
            with open(self.key_pub_file, "w") as f:
                f.write(key_pub_and_sign)
            return 1

    def exec(self, ip, port, commands, get_pty=1, user='root'):
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=3)
        """
        stdin, stdout, stderr=self.ssh.exec_command(commands)
        return stdin, stdout, stderr
        """
        status=self.ssh.exec_command(commands, get_pty=get_pty)
        #log.logger.debug(f"exec: {commands=}")
        return status

    def free_pass_set(self, ip, port, password, user='root'):
        "ssh-copy-id"

        with open(self.key_pub_file, "r") as f:
            key_pub=f.read()

        self.ssh.connect(ip, port=port, username=user, password=password, timeout=1)
        #self.ssh.exec_command("mkdir -p ~/.ssh; chmod 700 ~/.ssh")
        sftp=self.ssh.open_sftp()
        ssh_dir="/root/.ssh"
        try:
            sftp.stat(ssh_dir)
        except FileNotFoundError as e:
            sftp.mkdir(ssh_dir, 0o700)

        sftp_file=sftp.file(f"{ssh_dir}/authorized_keys", "a")
        sftp_file.write(key_pub)
        sftp_file.chmod(384)
        sftp_file.close()
        sftp.close()

    def scp(self, ip, port, user, local_file, remote_file):
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=3)
        sftp=self.ssh.open_sftp()
        result=sftp.put(local_file, remote_file, confirm=True)
        sftp.close()
        return result

    def get(self, ip, port, user, remote_file, local_file):
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=1)
        sftp=self.ssh.open_sftp()
        sftp.get(remote_file, local_file)
        sftp.close()

    def __del__(self):
        self.ssh.close()

