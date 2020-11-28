#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, rabbitmq_src, rabbitmq_dst, rabbitmq_pkg_dir, rabbitmq_version

def main():
    """
        将erlang.rpm放入rabbitmq.tar.gz的pkg目录中
    """
    action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    rabbitmq_dir=f"{located}/{rabbitmq_dst}"
    rabbitmq_info_dict=conf_dict["rabbitmq_info"]

    log=common.Logger({"remote": log_remote_level}, loggger_name="rabbitmq")

    rabbitmq_port=rabbitmq_info_dict["port"].get("rabbitmq_port")
    epmd_port=rabbitmq_info_dict["port"].get("epmd_port")
    beam_port=rabbitmq_info_dict["port"].get("beam_port")
    port_list=[
            rabbitmq_port, 
            epmd_port, 
            beam_port
            ]

    flag=0
    # 安装
    if action=="install":
        pkg_file=conf_dict["pkg_file"]
        value, msg=common.install(pkg_file, rabbitmq_src, rabbitmq_dst, rabbitmq_pkg_dir, located)
        if not value:
            log.logger.error(msg)
            flag=1
            sys.exit(flag)
            return 

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
                RABBITMQ_NODE_IP_ADDRESS=0.0.0.0
                RABBITMQ_DIST_PORT={beam_port}
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
                flag=1
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)

    elif action=="start":
        command=f"cd {rabbitmq_dir} && ./sbin/rabbitmq-server -detached" 
        log.logger.debug(f"{command=}")
        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
                flag=1
            else:
                log.logger.debug(f"检测端口: {port_list=}")
                if not common.port_exist(port_list):
                    flag=2
                else:
                    # 设置账号, vhost及权限
                    vhosts_list=conf_dict["rabbitmq_info"].get("vhosts")
                    users_list=conf_dict["rabbitmq_info"].get("users")
                    passwords_list=conf_dict["rabbitmq_info"].get("passwords")
                    if vhosts_list is not None and users_list is not None and passwords_list is not None:
                        log.logger.debug("添加账号权限")
                        for vhost, user, password in zip(vhosts_list, users_list, passwords_list):
                            account_command=f"rabbitmqctl add_user {user} {password} && rabbitmqctl add_vhost {vhost} && rabbitmqctl set_permissions -p {vhost} {user} '.*' '.*' '.*'"
                            log.logger.debug(f"{account_command=}")
                            status, result=common.exec_command(account_command)
                            if status:
                                if result.returncode != 0:
                                    log.logger.error(result.stderr)
                                    flag=1
                            else:
                                log.logger.error(result)
                                flag=1
        else:
            log.logger.error(result)
            flag=1

        sys.exit(flag)

if __name__ == "__main__":
    main()
