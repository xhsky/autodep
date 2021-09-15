#!/opt/python3/bin/python3
# *- coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, rabbitmq_src, rabbitmq_dst, rabbitmq_pkg_dir, erl_dst, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, rabbitmq_src, rabbitmq_dst, rabbitmq_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    # 配置
    ## cookie
    cookie_file="/root/.erlang.cookie"
    cookie_context="PWSZLCZPGCLCQZXICHRW"
    # mq配置
    cluster_name=rabbitmq_info_dict.get("cluster_name")
    erlang_mem=rabbitmq_info_dict.get("erlang_mem")
    members_list=rabbitmq_info_dict.get("members")
    node_type=rabbitmq_info_dict.get("node_type")

    mq_env_text=f"""\
            NODE_IP_ADDRESS=0.0.0.0
            DIST_PORT={beam_port}
            ERL_EPMD_PORT={epmd_port}
    """
    mq_env_file=f"{rabbitmq_dir}/etc/rabbitmq/rabbitmq-env.conf"
    mq_config_text=f"""\
        listeners.tcp.default = {rabbitmq_port}
        vm_memory_high_watermark.absolute = {erlang_mem}
        vm_memory_high_watermark_paging_ratio = 0.5
        log.file.level = info
        mnesia_table_loading_retry_timeout = 10000
        mnesia_table_loading_retry_limit = 3
        cluster_name={cluster_name}
        cluster_formation.peer_discovery_backend = classic_config
        cluster_formation.node_type = {node_type}
        """
    mq_config_file=f"{rabbitmq_dir}/etc/rabbitmq/rabbitmq.conf"

    members_nodes=""
    for index, item in enumerate(members_list):
        members_nodes=f"{members_nodes}\ncluster_formation.classic_config.nodes.{index+1}=rabbit@{item}"

    rabbitmq_sh_text=f"""\
            export RABBITMQ_HOME={rabbitmq_dir}
            export PATH=$RABBITMQ_HOME/sbin:$PATH
    """
    config_dict={
            "cookie_config":{
                "config_file": cookie_file, 
                "config_context": cookie_context, 
                "mode": "w"
                }, 
            "mq_env": {
                "config_file": mq_env_file, 
                "config_context": mq_env_text, 
                "mode": "w"
                }, 
            "mq_config":{
                "config_file": mq_config_file, 
                "config_context": mq_config_text, 
                "mode": "w"
                }, 
            "nodes_config":{
                "config_file": mq_config_file, 
                "config_context": members_nodes, 
                "mode": "a"
                }, 
            "rabbitmq_sh":{
                "config_file": "/etc/profile.d/rabbitmq.sh", 
                "config_context": rabbitmq_sh_text, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        # erlang cookie设置权限
        try: 
            log.logger.debug("设置erlang cookie文件权限")
            os.chmod(cookie_file, 0o400)
        except Exception as e:
            log.logger.error(str(e))
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    command=f"bash -lc 'cd {rabbitmq_dir} && ./sbin/rabbitmq-server -detached'" 
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=180):
            return_value=error_code
        else:
            # 设置账号, vhost及权限
            account_dict=conf_dict["rabbitmq_info"].get("account")
            if account_dict is not None:
                vhosts_list=account_dict.get("vhosts")
                users_list=account_dict.get("users")
                passwords_list=account_dict.get("passwords")
                #if vhosts_list is not None and users_list is not None and passwords_list is not None:
                log.logger.debug("添加账号权限")
                for vhost, user, password in zip(vhosts_list, users_list, passwords_list):
                    command=f"rabbitmqctl add_user {user} {password} && rabbitmqctl add_vhost {vhost} && rabbitmqctl set_permissions -p {vhost} {user} '.*' '.*' '.*'"
                    account_command=f"bash -lc '{command}'"
                    log.logger.debug(f"{account_command=}")
                    result, msg=common.exec_command(account_command)
                    if not result:
                        log.logger.error(msg)
                        return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def start():
    """启动
    """
    return_value=normal_code
    command=f"bash -lc 'cd {rabbitmq_dir} && ./sbin/rabbitmq-server -detached'" 
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=60):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def stop():
    """停止
    """
    return_value=normal_code
    command=f"bash -lc 'cd {rabbitmq_dir} && ./sbin/rabbitmqctl stop'" 
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)

    log.logger.debug(f"检测端口: {mq_port_list=}")
    if not common.port_exist(mq_port_list, exist_or_not=False):
        return_value=error_code
    else:
        command=f"cd {located}/{erl_dst} && ./bin/epmd -kill"
        log.logger.debug(f"{command=}")
        result, msg=common.exec_command(command)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if not common.port_exist(port_list, exist_or_not=False):
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
    rabbitmq_dir=f"{located}/{rabbitmq_dst}"
    rabbitmq_info_dict=conf_dict["rabbitmq_info"]

    log=common.Logger({"remote": log_remote_level}, loggger_name="rabbitmq")

    rabbitmq_port=rabbitmq_info_dict["port"].get("rabbitmq_port")
    epmd_port=rabbitmq_info_dict["port"].get("epmd_port")
    beam_port=rabbitmq_info_dict["port"].get("beam_port")
    mq_port_list=[
            rabbitmq_port, 
            beam_port
            ]

    port_list=[epmd_port]
    port_list.extend(mq_port_list)

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

