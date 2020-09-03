#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os
import subprocess
from libs.common import Logger

def main():
    hostname, hosts_str=sys.argv[1:]

    log=Logger(None, "info", "remote")
    hostname_cmd=f"hostnamectl set-hostname {hostname}"
    result=os.system(hostname_cmd)
    if result==0:
        log.logger.info(f"设置主机名为{hostname}完成")

    firewalld_cmd=f"systemctl disable firewalld; systemctl stop firewalld"
    result=os.system(firewalld_cmd)
    if result==0:
        log.logger.info(f"关闭防火墙完成")

    # 关闭selinux
    selinux_conf_file="/etc/selinux/config"
    mode_flag=0
    if os.path.exists(selinux_conf_file):
        with open(selinux_conf_file, "r") as f:
            text=f.readlines()
            enforce_mode="SELINUX=enforcing\n"
            disable_mode="SELINUX=disabled\n"
            if enforce_mode in text:
                text[text.index(enforce_mode)]=disable_mode
                mode_flag=1
        if mode_flag:
            with open(selinux_conf_file, "w") as f:
                f.writelines(text)
            result=os.system("setenforce 0 &> /dev/null")
        if result==0 or result==256:
            log.logger.info(f"关闭SELinux完成")

    # 更改nofile, nproc
    value=65536
    status, msg=subprocess.getstatusoutput("ulimit -n")
    nofile_value=int(msg)
    status, msg=subprocess.getstatusoutput("ulimit -u")
    nproc_value=int(msg)

    ulimit_conf_file="/etc/security/limits.conf"
    try:
        if nofile_value < value:
            with open(ulimit_conf_file, "a") as f:
                f.write("root - nofile 65536\n")
        if nproc_value < value:
            with open(ulimit_conf_file, "a") as f:
                f.write("root - nproc 65536\n")
        log.logger.info("用户权限已提升")
    except Except as e:
        log.logger.error(f"权限提升错误: {e}")

    # 配置hosts
    hosts_file="/etc/hosts"
    with open(hosts_file, "r") as f:
        host_text_list=f.readlines()
        host_list=hosts_str.split("\n")
        added_hosts=[]
        for i in host_list:
            i=f"{i}\n"          # 添加换行符
            if i not in host_text_list:
                added_hosts.append(i)
    with open(hosts_file, "a") as f:
        f.writelines(added_hosts)
    log.logger.info(f"hosts配置完成")

if __name__ == "__main__":
    main()
