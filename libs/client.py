#!/usr/bin/env python3
# coding:utf8
# sky

import paramiko
import socket, os

class client(object):
    def __init__(self, ip, port, username="root"):
        self.ip=ip
        self.port=port
        self.user=username
        self.ssh=paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

    def password_conn(self, password): 
        try:
            self.ssh.connect(self.ip, port=self.port, username=self.user, password=password, timeout=1)     # 正常连接
            status=0
        except paramiko.ssh_exception.NoValidConnectionsError as e:                                         # 端口无法连接
            status=1
        except paramiko.ssh_exception.AuthenticationException as e:                                         # 密码错误
            status=2
        except Exception as e:                                                                              # 未知错误
            status=3
        self.ssh.close()
        return status

    def gen_keys(self):
        """生成公私钥对"""
        pkey_file="~/.ssh/id_rsa"
        pkey_pub_file="~/.ssh/id_rsa.pub"

        if os.path.exists(pkey_file) and os.path.exists(pkey_pub_file):
            pass
        else:
            # 生成私钥文件
            key=paramiko.rsakey.RSAKey.generate(2048)
            key.write_private_key_file(pkey_file)
            # 生成公钥文件
            pub_key_file=key.get_base64()
            pub_key_sign="%s%s" % (" ".join(["ssh-rsa", pub_key_file]), "\n")
            with open(pkey_pub_file, "w") as f:
                f.write(pub_key_sign)
            self.__log.log("info", "已生成公私钥")

    def key_conn(self, hostname, password):
        pub_key_file="%s/sky_pkey.pub" % self.__key_dir

        with open(pub_key_file, "r") as f:
            pub_key=f.read()

        self.__ssh.connect(hostname, port=self.__port, username=self.__user, password=password, timeout=1)
        self.__ssh.exec_command("setenforce 0; mkdir -p ~/.ssh; chmod 700 ~/.ssh")
        
        sftp=self.__ssh.open_sftp()
        sftp_file=sftp.file("./.ssh/authorized_keys", "a")
        sftp_file.write(pub_key)
        sftp_file.chmod(384)
        sftp_file.close()
        sftp.close()
        self.__log.log("info", "%s 已完成免密码通信" % hostname)

    def exec(self, hostname, commands):
        pkey_file="%s/sky_pkey" % self.__key_dir
        self.__ssh.connect(hostname, port=self.__port, username=self.__user, key_filename=pkey_file, timeout=1)
        self.__ssh.exec_command(commands)
        
    def transfer(self, hostname, local_file, remote_file, remote_path):
        pkey_file="%s/sky_pkey" % self.__key_dir
        self.__ssh.connect(hostname, port=self.__port, username=self.__user, key_filename=pkey_file, timeout=1)
        sftp=self.__ssh.open_sftp()
        sftp.put(local_file, remote_file, confirm=True)
        self.__log.log("info", "安装包传输至%s:%s" % (hostname, remote_path))
        tar_command="tar -xf %s -C %s" % (local_file, remote_path)
        self.__ssh.exec_command(tar_command)
        self.__log.log("info", "%s上的安装包解压至%s" % (hostname, remote_path))
       sftp.close()

    def __del__(self):
        self.__ssh.close()

if __name__ == "__main__":
    #a={"192.168.1.122":"test1", "192.168.1.123":'test2'}
    #b=password_conn(a, username="test1")
    #print(b)

    #gen_keys()
    gen_keys()
    key_conn("192.168.1.123", "root", "111111")

