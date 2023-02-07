#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs.common import Logger, exec_command
from libs.env import log_remote_level, normal_code, error_code


def main():
    log=Logger({"remote": log_remote_level}, logger_name="init")
    return_value=0

    if os.path.exists("/etc/firewalld/firewalld.conf"):
        firewalld_cmd=f"systemctl disable firewalld && systemctl stop firewalld"
    elif os.path.exists("/etc/default/ufw"):
        firewalld_cmd=f"ufw disable"
    else:
        firewalld_cmd=""

    if firewalld_cmd!="":
        log.logger.info(f"关闭防火墙")
        log.logger.debug(f"{firewalld_cmd=}")
        result, msg=exec_command(firewalld_cmd)
        if not result:
            log.logger.error(f"关闭防火墙失败: {msg}")
            return_value=error_code

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
            result, msg=exec_command("getenforce")
            if result:
                if msg.lower().strip()!="disabled":
                    result, msg=exec_command("setenforce 0")
                    if not result:
                        log.logger.error(f"关闭SELinux失败: {msg}")
                        return_value=error_code
            else:
                log.logger.error(f"获取SELinux状态失败: {msg}")
                return_value=error_code

    # 更改nofile, nproc
    value=65536
    ulimit_conf_file="/etc/security/limits.conf"

    result, msg=exec_command("bash -c 'ulimit -n'")
    if result:
        if msg.isdigit():
            nofile_value=int(msg)
            if nofile_value < value:
                with open(ulimit_conf_file, "a") as f:
                    f.write("root - nofile 65536\n")
                log.logger.info(f"设置nofile值为{value}")
        else:
            log.logger.info(f"nofile值为{msg}")
    else:
        log.logger.error(f"获取nofile失败: {msg}")
        return_value=error_code

    result, msg=exec_command("bash -c 'ulimit -u'")
    if result:
        nproc_value=int(msg)
        if nproc_value < value:
            with open(ulimit_conf_file, "a") as f:
                f.write("root - nproc 65536\n")
            log.logger.info(f"设置nproc值为{value}")
    else:
        log.logger.error(f"获取nproc失败: {msg}")
        return_value=error_code

    # 调整内核参数
    sys_net_file="/etc/sysctl.d/user.conf"
    net_config="""\
            net.ipv4.tcp_max_syn_backlog=8192
            net.core.somaxconn=8192
            net.core.netdev_max_backlog=10240
            net.ipv4.tcp_max_tw_buckets = 5000
            net.ipv4.tcp_tw_reuse = 1
            net.ipv4.tcp_syncookies = 1
            net.ipv4.tcp_abort_on_overflow = 1
            net.ipv4.tcp_fin_timeout = 30
            net.ipv4.tcp_slow_start_after_idle = 0
            vm.swappiness = 5
    """
    with open(sys_net_file, "w") as f:
        f.write(net_config)
    result, msg=exec_command(f"sysctl -p {sys_net_file}")
    if not result:
        log.logger.error(f"内核优化调整失败: {msg}")
        return_value=error_code

    sys.exit(return_value)

if __name__ == "__main__":
    main()
