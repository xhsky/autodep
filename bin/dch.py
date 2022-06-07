#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs import common, tools
from libs.env import log_remote_level, dch_src, dch_dst, dch_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, dch_src, dch_dst, None, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    dch_mem=dch_info_dict["db_info"].get("dch_mem")
    # 环境配置
    log.logger.debug("环境配置")
    sysctl_conf_file="/etc/sysctl.d/dch.conf"
    sysctl_conf_text="""\
            net.core.somaxconn=2048
            vm.overcommit_memory=1
    """
    dch_sh_text=f"""\
            export DCH_HOME={dch_dir}
            export PATH=$DCH_HOME/bin:$PATH
    """
    hugepage_disabled=f"echo never > /sys/kernel/mm/transparent_hugepage/enabled\n"
    config_dict={
            "sysctl_conf":{
                "config_file": sysctl_conf_file, 
                "config_context": sysctl_conf_text, 
                "mode": "w"
                }, 
            "rc_local":{
                "config_file": "/etc/rc.local", 
                "config_context": hugepage_disabled, 
                "mode": "r+"
                }, 
            "dch_sh":{
                "config_file": "/etc/profile.d/dch.sh", 
                "config_context": dch_sh_text, 
                "mode": "w"
                }
            }

    # dch配置, 根据主从配置dch文件
    log.logger.debug("配置dch")
    if dch_info_dict.get("cluster_info") is None:
        role="stand-alone"
    else:
        cluster_info_dict=dch_info_dict["cluster_info"]
        role=cluster_info_dict.get("role")
    log.logger.debug(f"{role=}")

    if role=="stand-alone" or role=="master":
        slaveof_master_port=""
    elif role=="slave":
        master_host=cluster_info_dict.get("master_host")
        master_port=cluster_info_dict.get("master_port")
        slaveof_master_port=f"replicaof {master_host} {master_port}"
    log.logger.debug(f"{slaveof_master_port=}")

    dch_io_threads=dch_info_dict["db_info"]["dch_io_threads"]
    dch_conf_text=tools.render("../config/templates/dch/dch.conf.tem", dch_info_dict=dch_info_dict, dch_dir=dch_dir)

    dch_enabled_text=dch_start_command
    config_dict.update(
            {
                "dch_conf": {
                    "config_file": f"{dch_dir}/conf/dch.conf",
                    "config_context": dch_conf_text,
                    "mode": "w"
                    },
                "dch_enabled": {
                    "config_file": "/etc/rc.local",
                    "config_context": dch_enabled_text, 
                    "mode": "r+"
                    }
                } 
            )

    # Sentinel配置
    if sentinel_flag:
        log.logger.debug("配置sentinel")
        monitor_host=sentinel_info.get("monitor_host")
        monitor_port=sentinel_info.get("monitor_port")
        replicas_num=len(sentinel_info.get("replicas_members"))

        if replicas_num <= 2:
            quorum=1
        elif (replicas_num % 2)==0:
            quorum=replicas_num/2
        else:
            quorum=int(replicas_num/2)+1
        sentinel_conf_text=tools.render("../config/templates/dch/sentinel.conf.tem", sentinel_info=sentinel_info, dch_dir=dch_dir, quorum=quorum)

        sentinel_enabled_text=dch_start_command
        config_dict.update(
                {
                    "sentinel_conf": {
                        "config_file": f"{dch_dir}/conf/sentinel.conf",
                        "config_context": sentinel_conf_text,
                        "mode": "w"
                        }, 
                    "dch_sentinel_enabled": {
                        "config_file": "/etc/rc.local",
                        "config_context": sentinel_enabled_text, 
                        "mode": "r+"
                        }
                    }
                )

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        command=f"sysctl -p {sysctl_conf_file} && echo never > /sys/kernel/mm/transparent_hugepage/enabled"
        log.logger.debug(f"刷新配置: {command=}")
        result=common.exec_command(command)
        if not result:
            log.logger.error(msg)
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    log.logger.debug(f"dch启动: {dch_start_command=}")
    result, msg=common.exec_command(dch_start_command)
    if result:
        log.logger.debug(f"检测端口: {dch_port} ")
        if not common.port_exist([dch_port]):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        log.logger.debug(f"sentinel启动: {sentinel_start_command=}")
        result, msg=common.exec_command(sentinel_start_command)
        if result:
            log.logger.debug(f"检测端口: {sentinel_port} ")
            if not common.port_exist([sentinel_port]):
                return_value=error_code
        else:
            log.logger.error(msg)
            return_value=error_code
    return return_value

def start():
    """启动
    """
    return run()

def stop():
    """停止
    """
    return_value=normal_code
    dch_stop_command=f"cd {dch_dir} && bin/dch-cli -p {dch_port} -a {dch_password} shutdown "
    log.logger.debug(f"dch停止: {dch_stop_command=}")
    result, msg=common.exec_command(dch_stop_command)
    if result:
        log.logger.debug(f"检测端口: {dch_port}")
        if not common.port_exist([dch_port], exist_or_not=False):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        if sentinel_password_str == "":
            sentinel_stop_command=f"cd {dch_dir} && bin/dch-cli -p {sentinel_port} shutdown"
        else:
            sentinel_stop_command=f"cd {dch_dir} && bin/dch-cli -a {sentinel_password} -p {sentinel_port} shutdown"
        log.logger.debug(f"sentinel停止: {sentinel_stop_command=}")
        result, msg=common.exec_command(sentinel_stop_command)
        if result:
            log.logger.debug(f"检测端口: {sentinel_port}")
            if not common.port_exist([sentinel_port], exist_or_not=False):
                return_value=error_code
        else:
            log.logger.error(msg)
            return_value=error_code
    return return_value

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    log=common.Logger({"remote": log_remote_level}, loggger_name="dch")

    if dch_dst is None:
        dch_dir=f"{located}/{dch_src}"
    else:
        dch_dir=f"{located}/{dch_dst}"
    dch_info_dict=conf_dict[f"{softname}_info"]
    dch_port=dch_info_dict["db_info"]["dch_port"]
    dch_password=dch_info_dict["db_info"].get("dch_password")
    port_list=[dch_port]

    dch_start_command=f"cd {dch_dir} && bin/dch-server conf/dch.conf"

    # 是否启用sentinel
    sentinel_info=dch_info_dict.get("sentinel_info")
    if  sentinel_info is None:
        sentinel_flag=0
    else:
        sentinel_flag=1
        sentinel_start_command=f"cd {dch_dir} && bin/dch-sentinel conf/sentinel.conf"
        sentinel_port=sentinel_info.get("sentinel_port")
        port_list.append(sentinel_port)
        sentinel_password=sentinel_info.get("sentinel_password")
        if sentinel_password is None or sentinel_password.strip()=="":
            sentinel_password_str=""
        else:
            sentinel_password_str=f"requirepass {sentinel_password}"

    if action=="install":
        sys.exit(install())
    elif action=="run":
        sys.exit(run())
    elif action=="start":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(activated_code)
        elif status_value==stopped_code:
            sys.exit(start())
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action=="stop":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(stop())
        elif status_value==stopped_code:
            sys.exit(stopped_code)
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action=="monitor":
        sys.exit(monitor())
    else:
        sys.exit(error_code)
