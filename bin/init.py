#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs.common import Logger, exec_command
from libs.env import log_remote_level

def main():
    log=Logger({"remote": log_remote_level}, logger_name="init")
    return_value=0

    log.logger.info(f"关闭防火墙")
    firewalld_cmd=f"systemctl disable firewalld && systemctl stop firewalld"
    log.logger.debug(f"{firewalld_cmd=}")
    result, msg=exec_command(firewalld_cmd)
    if not result:
        log.logger.error(f"关闭防火墙失败: {msg}")
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
            status, result=exec_command("setenforce 0")
            if status:
                if result.returncode != 0 and result.returncode != 256:
                    return_value=1
                    log.logger.error(f"关闭SELinux失败: {result.stderr}")
            else:
                return_value=1
                log.logger.error(f"关闭SELinux失败: {result}")

    # 更改nofile, nproc
    value=65536
    ulimit_conf_file="/etc/security/limits.conf"

    result, msg=exec_command("ulimit -n")
    if result:
        nofile_value=int(msg)
        if nofile_value < value:
            with open(ulimit_conf_file, "a") as f:
                f.write("root - nofile 65536\n")
            log.logger.info(f"设置nofile值为{value}")
    else:
        log.logger.error(f"获取nofile失败: {msg}")
        return_value=1

    result, msg=exec_command("ulimit -u")
    if result:
        nproc_value=int(msg)
        if nproc_value < value:
            with open(ulimit_conf_file, "a") as f:
                f.write("root - nproc 65536\n")
            log.logger.info(f"设置nproc值为{value}")
    else:
        log.logger.error(f"获取nproc失败: {msg}")
        return_value=1

    sys.exit(return_value)

if __name__ == "__main__":
    main()
