#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-26 11:21:38
# sky

import paramiko
import pymysql
import os, json
from libs.common import Logger
from libs.env import log_file, log_file_level, remote_python_exec, \
        located_dir_link, autocheck_dst

log=Logger({"file": log_file_level}, logger_name="remote", log_file=log_file)

class soft(object):
    """
    软件控制	
    """
    def  __init__(self, ip, port, ssh_client):
        self.ip=ip
        self.port=port
        self.ssh_client=ssh_client

    def init(self, py_file):
        command=f"{remote_python_exec} {py_file}"
        log.logger.debug(f"init: {command}")
        status=self.ssh_client.exec(self.ip, self.port, command)
        return status

    def sendmail(self, py_file, args_dict):
        command=f"cd {located_dir_link}/{autocheck_dst} ; {remote_python_exec} {py_file} 'autocheck' sendmail '{json.dumps(args_dict)}'"
        log.logger.debug(f"sendmail: {command}")
        status=self.ssh_client.exec(self.ip, self.port, command)
        return status

    def remote_exec(self, py_file, softname, action, args_dict):
        """
        用于install, run, start, stop, 非init
        """
        command=f"{remote_python_exec} {py_file} {softname} {action} '{json.dumps(args_dict)}'"
        log.logger.debug(f"{action=}: {command}")
        status=self.ssh_client.exec(self.ip, self.port, command)
        return status

    def install(self, py_file, softname, args_dict):
        status=self.remote_exec(py_file, softname, "install", args_dict)
        return status

    def run(self, py_file, softname, args_dict):
        status=self.remote_exec(py_file, softname, "run", args_dict)
        return status

    def start(self, py_file, softname, args_dict):
        status=self.remote_exec(py_file, softname, "start", args_dict)
        return status

    def stop(self, py_file, softname, args_dict):
        status=self.remote_exec(py_file, softname, "stop", args_dict)
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
            self.ssh.connect(ip, port=port, username=user, password=password, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)     # 正常连接
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
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
        """
        stdin, stdout, stderr=self.ssh.exec_command(commands)
        return stdin, stdout, stderr
        """
        try:
            status=self.ssh.exec_command(commands, get_pty=get_pty)
        except Exception as e:
            return str(e)
        return status

    def free_pass_set(self, ip, port, password, user='root'):
        "ssh-copy-id"

        with open(self.key_pub_file, "r") as f:
            key_pub=f.read()

        self.ssh.connect(ip, port=port, username=user, password=password, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
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
        self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
        sftp=self.ssh.open_sftp()
        result=sftp.put(local_file, remote_file, confirm=True)
        sftp.close()
        return result

    def get(self, ip, port, user, remote_file, local_file):
        try:
            self.ssh.connect(ip, port=port, username=user, key_filename=self.key_file, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
            sftp=self.ssh.open_sftp()
            sftp.get(remote_file, local_file)
            sftp.close()
            return True
        except Exception as e:
            return str(e)

    def __del__(self):
        self.ssh.close()

class DB(object):
    """
    数据库操作
    """
    def __init__(self, db_type, host, port, user, password, db_name, **kwargs):
        self._db_type=db_type
        if self._db_type.lower()=="mysql":
            self.conn=pymysql.connect(host=host, port=port, user=user, passwd=password, db=db_name, charset='utf8mb4')
            self.cursor=self.conn.cursor()

    def exec(self, sql):
        self.cursor.execute(sql)

    def commit(self):
        self.conn.commit()

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass
