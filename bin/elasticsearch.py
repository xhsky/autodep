#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, elasticsearch_src, elasticsearch_dst, elasticsearch_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code


'''
def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    es_dir=f"{located}/{elasticsearch_dst}"

    log=common.Logger({"remote": log_remote_level}, loggger_name="es")

    http_port=conf_dict["elasticsearch_info"]["port"]["http_port"]
    transport=conf_dict["elasticsearch_info"]["port"]["transport"]
    port_list=[
            http_port, 
            transport
            ]

    flag=0
    # 安装
    if action=="install":
        pkg_file=conf_dict["pkg_file"]
        command="id -u elastic &> /dev/null || useradd elastic"
        log.logger.debug(f"创建用户: {command=}")
        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
        else:
            log.logger.error(result)
        value, msg=common.install(pkg_file, elasticsearch_src, elasticsearch_dst, elasticsearch_pkg_dir, located)
        if not value:
            log.logger.error(msg)
            flag=1
            sys.exit(flag)

        # 配置
        ## es配置
        jvm_mem=conf_dict["elasticsearch_info"]["jvm_mem"]
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
            http.port: {http_port}
            discovery.seed_hosts: {members_list}
            transport.tcp.port: {transport}
            cluster.initial_master_nodes: {members_list}
            gateway.recover_after_nodes: 1
            action.destructive_requires_name: true
        """

        jvm_config_file=f"{es_dir}/config/jvm.options"
        with open(jvm_config_file, "r+") as f:
            raw_text=f.readlines()
            xms_index=raw_text.index('-Xms1g\n')
            xmx_index=raw_text.index('-Xmx1g\n')
            raw_text[xms_index]=f"-Xms{jvm_mem}\n"
            raw_text[xmx_index]=f"-Xmx{jvm_mem}\n"
            f.seek(0)
            f.writelines(raw_text)

        add_java_file=f"{es_dir}/bin/elasticsearch-env"          # 将es自身的java环境写入脚本, 防止与其他JAVA_HOME变量冲突
        with open(add_java_file, "r+") as f:
            raw_text=f.readlines()
            java_home=f"export JAVA_HOME={es_dir}/jdk\n"
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
                    "config_file": f"{es_dir}/config/elasticsearch.yml", 
                    "config_context": es_config_text, 
                    "mode": "w"
                    }
                }
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
        result, msg=common.config(config_dict)
        if result:
            command=f"chown -R elastic:elastic {located}/{elasticsearch_src}*  && sysctl -p {sysctl_conf_file}"
            log.logger.debug(f"配置环境: {command=}")
            status, result=common.exec_command(command)
            if status:
                if result.returncode != 0:
                    log.logger.error(result.stderr)
                    flag=1
            else:
                log.logger.error(result)
                flag=1  
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)

    elif action == "run" or action=="start":
        command=f"su elastic -l -c 'cd {es_dir} && ./bin/elasticsearch -d -p elasticsearch.pid &> /dev/null'" 
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
            log.logger.error(result)
            flag=1

        sys.exit(flag)

    elif action=="stop":
        command=f"su elastic -l -c 'cd {es_dir} && kill `cat elasticsearch.pid`'" 
        log.logger.debug(f"{command=}")

        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
                flag=1
            else:
                log.logger.debug(f"检测端口: {port_list=}")
                if common.port_exist(port_list, exist_or_not=0):
                    flag=2
        else:
            log.logger.error(result)
            flag=1

        sys.exit(flag)
'''

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    command="id -u elastic &> /dev/null || useradd elastic"
    log.logger.debug(f"创建用户: {command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
    value, msg=common.install(pkg_file, elasticsearch_src, elasticsearch_dst, elasticsearch_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # 配置
    ## es配置
    jvm_mem=conf_dict["elasticsearch_info"]["jvm_mem"]
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
        http.port: {http_port}
        discovery.seed_hosts: {members_list}
        transport.tcp.port: {transport}
        cluster.initial_master_nodes: {members_list}
        gateway.recover_after_nodes: 1
        action.destructive_requires_name: true
    """

    jvm_config_file=f"{es_dir}/config/jvm.options"
    with open(jvm_config_file, "r+") as f:
        raw_text=f.readlines()
        xms_index=raw_text.index('-Xms1g\n')
        xmx_index=raw_text.index('-Xmx1g\n')
        raw_text[xms_index]=f"-Xms{jvm_mem}\n"
        raw_text[xmx_index]=f"-Xmx{jvm_mem}\n"
        f.seek(0)
        f.writelines(raw_text)

    add_java_file=f"{es_dir}/bin/elasticsearch-env"          # 将es自身的java环境写入脚本, 防止与其他JAVA_HOME变量冲突
    with open(add_java_file, "r+") as f:
        raw_text=f.readlines()
        java_home=f"export JAVA_HOME={es_dir}/jdk\n"
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
                "config_file": f"{es_dir}/config/elasticsearch.yml", 
                "config_context": es_config_text, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        command=f"chown -R elastic:elastic {located}/{elasticsearch_src}*  && sysctl -p {sysctl_conf_file}"
        log.logger.debug(f"配置环境: {command=}")
        result, msg=common.exec_command(command)
        if not result:
            log.logger.error(result)
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    command=f"su elastic -l -c 'cd {es_dir} && ./bin/elasticsearch -d -p elasticsearch.pid &> /dev/null'" 
    log.logger.debug(f"{command=}")

    result, msg=common.exec_command(command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
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
    command=f"su elastic -l -c 'cd {es_dir} && kill `cat elasticsearch.pid`'" 
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
    log=common.Logger({"remote": log_remote_level}, loggger_name="es")

    located=conf_dict.get("located")
    es_dir=f"{located}/{elasticsearch_dst}"

    http_port=conf_dict["elasticsearch_info"]["port"]["http_port"]
    transport=conf_dict["elasticsearch_info"]["port"]["transport"]
    port_list=[
            http_port, 
            transport
            ]

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
