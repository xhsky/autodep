#!/usr/bin/env python3
# coding:utf8
# sky

import paramiko
import os

class Client(object):
    def __init__(self):
        self.ssh=paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self.key_dir="/root/.ssh"
        self.key_file=f"{self.key_dir}/id_rsa"
        self.key_pub_file=f"{self.key_dir}/id_rsa.pub"

    def password_conn(self, ip, port, password, user='root'): 
        try:
            self.ssh.connect(ip, port=port, username=user, password=password, timeout=1)     # 正常连接
            status=0
            msg="正常连接"
        except paramiko.ssh_exception.NoValidConnectionsError as e:                                         # 端口无法连接
            status=1
            msg="端口无法连接"
        except paramiko.ssh_exception.AuthenticationException as e:                                         # 密码错误
            status=2
            msg="密码错误"
        except Exception as e:                                                                              # 未知错误
            status=3
            msg="未知错误, 无法连接"
        self.ssh.close()
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

    def exec(self, ip, port, commands, user='root'):
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=1)
        stdin, stdout, stderr=self.ssh.exec_command(commands)
        return stdout

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
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=1)
        sftp=self.ssh.open_sftp()
        sftp.put(local_file, remote_file, confirm=True)
        """
        tar_command="tar -xf %s -C %s" % (local_file, remote_path)
        self.__ssh.exec_command(tar_command)
        self.__log.log("info", "%s上的安装包解压至%s" % (hostname, remote_path))
        """
        sftp.close()

    def __del__(self):
        self.ssh.close()

if __name__ == "__main__":
    a=Client()

    #gen_keys()
    a.gen_keys()
    #status=a.password_conn("192.168.1.174", 22, "dreamsoft")
    a.free_pass_set("192.168.1.174", 22, "dreamsoft")
    #a.free_pass_set("192.168.1.173", 22, "dreamsoft")
    #msg=a.exec("192.168.1.174", 22, "df -h")
    #a.scp("192.168.1.174", 22, "root", "/tmp/b", "/root/b")

