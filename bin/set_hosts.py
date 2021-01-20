#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2021-01-20 10:55:49
# sky

import sys, json
from libs.common import Logger, exec_command
from libs.env import log_remote_level

def main():
    log=Logger({"remote": log_remote_level}, logger_name="set_hosts")
    return_value=0

    try:
        args_json=sys.argv[1]
        args=json.loads(args_json)
        hostname=args["hostname"]
        hosts_list=args["hosts"]

        log.logger.info(f"设置主机名为{hostname}")
        hostname_cmd=f"hostnamectl set-hostname {hostname}"
        log.logger.debug(f"{hostname_cmd=}")
        status, result=exec_command(hostname_cmd)
        if status:
            if result.returncode != 0:
                log.logger.error(f"设置主机名失败: {result.stderr}")
                return_value=1
        else:
            log.logger.error(f"设置主机名失败: {result}")
            return_value=1

        # 配置hosts
        hosts_file="/etc/hosts"
        with open(hosts_file, "r") as f:
            host_text_list=f.readlines()
            added_hosts=[]
            for hosts in hosts_list:
                hosts=f"{hosts}\n"          # 添加换行符
                if hosts not in host_text_list:
                    added_hosts.append(hosts)
        with open(hosts_file, "a") as f:
            f.writelines(added_hosts)
        log.logger.info(f"hosts配置完成")
    except Exception as e:
        log.logger.error(f"hosts配置失败: {e}")
        return_value=1
    
    return return_value
    
if __name__ == "__main__":
    main()
