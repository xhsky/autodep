#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2021-01-20 10:55:49
# sky

import sys, json, os
from libs.common import Logger, exec_command
from libs.env import log_remote_level, normal_code, error_code, \
        located_dir_link

def main():
    """设置主机名, 填写hosts
    """
    log=Logger({"remote": log_remote_level}, logger_name="set_hosts")
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    hosts_info_dict=conf_dict["hosts_info"]
    located=conf_dict["located"]
    return_value=normal_code

    try:
        hostname=hosts_info_dict["hostname"]
        hosts_list=hosts_info_dict["hosts"]

        # 设置主机名
        log.logger.info(f"设置主机名为{hostname}")
        hostname_cmd=f"hostnamectl set-hostname {hostname}"
        log.logger.debug(f"{hostname_cmd=}")
        result, msg=exec_command(hostname_cmd)
        if not result:
            log.logger.error(f"设置主机名失败: {msg}")
            return_value=error_code

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

        # 建立安装目录
        log.logger.info(f"建立安装目录: {located}")
        os.makedirs(located, exist_ok=1)
        if located != located_dir_link:
            if os.path.islink(located_dir_link):
                if os.readlink(located_dir_link) != located:
                    os.remove(located_dir_link)
                    os.symlink(located, located_dir_link)
            else:
                log.logger.error(f"{located_dir_link}目录存在, 无法安装, 请移除该目录!")
                return_value=error_code
    except Exception as e:
        log.logger.error(f"{str(e)}")
        return_value=error_code
    return return_value
    
if __name__ == "__main__":
    main()
