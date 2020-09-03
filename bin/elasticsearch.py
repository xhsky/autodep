#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
import psutil
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    soft_name="ElasticSearch"
    log=common.Logger(None, "info", "remote")
    src="elasticsearch-"
    dst="es"

    # 安装
    if action=="install":
        os.system("id -u elastic &> /dev/null || useradd elastic")
        value, msg=common.install(soft_file, src, dst, None, located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")
            return 

        # 配置
        ## es配置
        mem=psutil.virtual_memory()
        jvm_mem=int(mem[0] * float(weight) /1024/1024)
        cluster_name=conf_dict["elasticsearch_info"]["cluster_name"]
        members_list=conf_dict["elasticsearch_info"]["members"]

        es_config_text=f"""\
            cluster.name: {cluster_name}
            #"node.name: es_node
            node.master: true
            node.voting_only: false
            node.data: true
            node.ingest: true
            bootstrap.memory_lock: true
            network.host: 0.0.0.0
            http.port: 9200
            discovery.seed_hosts: {members_list}
            transport.tcp.port: 9300
            cluster.initial_master_nodes: {members_list}
            gateway.recover_after_nodes: 1
            action.destructive_requires_name: true
        """

        jvm_config_file=f"{located}/{dst}/config/jvm.options"
        with open(jvm_config_file, "r+") as f:
            raw_text=f.readlines()
            xms_index=raw_text.index('-Xms1g\n')
            xmx_index=raw_text.index('-Xmx1g\n')
            raw_text[xms_index]=f"-Xms{jvm_mem}m\n"
            raw_text[xmx_index]=f"-Xmx{jvm_mem}m\n"
            f.seek(0)
            f.writelines(raw_text)

        add_java_file=f"{located}/{dst}/bin/elasticsearch-env"          # 将es自身的java环境写入脚本, 防止与其他JAVA_HOME变量冲突
        with open(add_java_file, "r+") as f:
            raw_text=f.readlines()
            java_home=f"export JAVA_HOME={located}/{dst}/jdk\n"
            raw_text.insert(2, java_home)
            f.seek(0)
            f.writelines(raw_text)

        ## 环境配置
        limit_conf_context="""\
            elastic    -   memlock unlimited
            elastic    -   fsize   unlimited
            elastic    -   as  unlimited
            elastic    -   nofile  65536
            elastic    -   nproc   65536
            """
        sysctl_conf_context="vm.max_map_count=262144"
        sysctl_conf_file="/etc/sysctl.d/es.conf" 

        config_dict={
                "limit_conf": {
                    "config_file": "/etc/security/limits.d/elastic.conf", 
                    "config_context": limit_conf_context, 
                    "mode": "w"
                    }, 
                "sysctl_conf": {
                    "config_file": sysctl_conf_file, 
                    "config_context": sysctl_conf_context, 
                    "mode": "w"
                    }, 
                "es_config_text": {
                    "config_file": f"{located}/{dst}/config/elasticsearch.yml", 
                    "config_context": es_config_text, 
                    "mode": "w"
                    }
                }
        result, msg=common.config(config_dict)
        if result==1:
            result=os.system(f"chown -R elastic:elastic {located}/{src}* &> /dev/null ; sysctl -p {sysctl_conf_file} &> /dev/null")
            if result==0:
                log.logger.info(f"{soft_name}配置完成")
            else:
                log.logger.error(f"{soft_name}环境变量未生效: {result}")
        else:
            log.logger.error(f"{soft_name}写入配置失败: {msg}")

    elif action=="start":
        command=f"su elastic -l -c 'cd {located}/{dst}; ./bin/elasticsearch -d -p elasticsearch.pid'" 
        result=os.system(command)
        if result==0:
            if common.port_exist(9200):
                log.logger.info(f"{soft_name}启动完成")
            else:
                log.logger.error(f"{soft_name}启动超时")
        else:
            log.logger.error(f"{soft_name}启动失败")

if __name__ == "__main__":
    main()
