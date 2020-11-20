#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import subprocess
from libs.common import Logger, port_connect

def main():
    log=Logger({"remote":"debug"})

    return_value=0
    args_json=sys.argv[1]
    log.logger.debug(f"{args_json=}")
    args=json.loads(args_json)

    hostname=args["hostname"]
    hosts_str=args["hosts"]


    log.logger.info(f"设置主机名为{hostname}...")
    hostname_cmd=f"hostnamectl set-hostname {hostname}"
    log.logger.debug(f"{hostname_cmd=}")
    result=os.system(hostname_cmd)
    if result != 0:
        log.logger.error(f"设置主机名失败")
        return_value=1

    log.logger.info(f"关闭防火墙...")
    firewalld_cmd=f"systemctl disable firewalld && systemctl stop firewalld"
    log.logger.debug(f"{firewalld_cmd=}")
    result=os.system(firewalld_cmd)
    if result != 0:
        log.logger.info(f"关闭防火墙失败...")
        return_value=1

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
            log.logger.info(f"关闭SELinux")
            with open(selinux_conf_file, "w") as f:
                f.writelines(text)
            result=os.system("setenforce 0")
            if result != 0 and result != 256:
                return_value=1
                log.logger.info(f"关闭SELinux失败")

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
    except Exception as e:
        log.logger.error(f"权限提升错误: {e}")
        return_value=1

    # 配置hosts
    try:
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
    except Exception as e:
        log.logger.error(f"hosts配置失败")
        return_value=1

    # 接口链通测试
    for interface in args["interface"]:
        if port_connect(args["interface"][interface][0], args["interface"][interface][1]):
            log.logger.info(f"{interface}接口连通")
        else:
            log.logger.warning(f"{interface}接口无法连通")
            return_value=1

    sys.exit(return_value)

if __name__ == "__main__":
    main()
