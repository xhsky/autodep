#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
import psutil 
from libs import common

def main():
    """
        将erlang.rpm放入rabbitmq.tar.gz的pkg目录中
    """
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    soft_name="RabbitMQ"
    rabbitmq_port=5672
    dst="rabbitmq"
    log=common.Logger("None", "info", "remote")

    # 安装
    if action=="install":
        value, msg=common.install(soft_file, "rabbitmq_server-", dst, "pkg", located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败")

        # 配置
        ## cookie
        cookie_file="/root/.erlang.cookie"
        cookie_context="PWSZLCZPGCLCQZXICHRW"
        # mq配置
        mem=psutil.virtual_memory()
        erlang_mem=int(mem[0] * float(weight) /1024/1024)
        cluster_name=conf_dict["rabbitmq_info"]["cluster_name"]
        members_list=conf_dict["rabbitmq_info"]["members"]
        node_type=conf_dict["rabbitmq_info"]["node_type"]

        mq_config_text=f"""\
            listeners.tcp.default = {rabbitmq_port}
            vm_memory_high_watermark.absolute={erlang_mem}M
            vm_memory_high_watermark_paging_ratio = 0.5
            log.file.level = info
            cluster_name={cluster_name}
            cluster_formation.peer_discovery_backend = classic_config
            cluster_formation.node_type = {node_type}
            """
        mq_config_file=f"{located}/rabbitmq/etc/rabbitmq/rabbitmq.conf"

        members_nodes=""
        for index, item in enumerate(members_list):
            members_nodes=f"{members_nodes}\ncluster_formation.classic_config.nodes.{index+1}=rabbit@{item}"

        config_dict={
                "cookie_config":{
                    "config_file": cookie_file, 
                    "config_context": cookie_context, 
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
                    }
                }
        result, msg=common.config(config_dict)
        if result == 1:
            log.logger.info(f"{soft_name}配置优化完成")
        else:
            log.logger.error(f"{soft_name}配置优化失败: {msg}")

        # erlang cookie设置权限
        try: 
            os.chmod(cookie_file, 0o400)
            log.logger.info("erlang cookie设置完成")
        except Exception as e:
            log.logger.info(f"erlang cookie设置失败: {e}")

    elif action=="start":
        command=f"cd {located}/{dst} ; ./sbin/rabbitmq-server -detached" 
        result=os.system(command)
        if result==0:
            status=common.port_exist(rabbitmq_port)
            if status==1:
                log.logger.info(f"{soft_name}启动完成")
            else:
                log.logger.error(f"{soft_name}启动超时")
        else:
            log.logger.error(f"{soft_name}启动失败")

if __name__ == "__main__":
    main()
