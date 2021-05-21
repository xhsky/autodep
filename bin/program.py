#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, requests, yaml
from libs import common
from libs.env import log_remote_level, normal_code, error_code, activated_code, stopped_code, abnormal_code

def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    program_info_dict=conf_dict[f"{softname}_info"]
    port_list=[program_info_dict["port"]]
    program_dir=program_info_dict['program_dir']

    log=common.Logger({"remote": log_remote_level}, loggger_name="jar")

    # 安装
    flag=0
    if action=="install":
        sys.exit(flag)
    elif action=="run":
        sys.exit(flag)
    elif action=="start":
        jvm_mem=program_info_dict["jvm_mem"]
        for jar_name in os.listdir(program_dir):
            if jar_name.endswith(".jar"):
                jar=jar_name
                break
        config=["application-prod.yml", "application-prod.properties"]
        for config_file in os.listdir(program_dir):
            if config_file in config:
                config_name=config_file
                break
        start_command=f"cd {program_dir} ; nohup java -Xms{jvm_mem} -Xmx{jvm_mem} -jar {jar} --server.port={port_list[0]} --spring.profiles.active=prod &> jar.log &"
        log.logger.debug(f"{start_command=}")
        result, msg=common.exec_command(start_command)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if not common.port_exist(port_list, seconds=600):
                flag=2
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)
    elif action=="stop":
        for port in port_list:
            pid=common.find_pid(port)
            log.logger.debug(f"{port=}, {pid=}")
            if pid != 0:
                stop_command=f"kill -9 {pid}"
                log.logger.debug(f"{stop_command=}")
                result, msg=common.exec_command(stop_command)
                if result:
                    log.logger.debug(f"检测端口: {port_list=}")
                    if not common.port_exist(port_list, exist_or_not=False):
                        flag=2
                else:
                    log.logger.error(msg)
                    flag=1
            else:
                log.logger.warning(f"{softname}未运行")
                flag=1
        sys.exit(flag)
    elif action=="heapdump":
        command=f"jmap -dump:format=b, file=heapdump.dump {pid}"
        log.logger.debug(f"{start_command=}")
        result, msg=common.exec_command(start_command)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if not common.port_exist(port_list, seconds=600):
                flag=2
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)

def install():
    """安装
    """
    return_value=0
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, "jar", None, None, program_dir)
    if not value:
        log.logger.error(msg)
        return error_code
    return return_value

def run():
    """运行
    """
    headers={
            "Content-Type": "application/json" 
            }
    nacos_host=program_info_dict["nacos_config"]["nacos_host"]
    nacos_port=program_info_dict["nacos_config"]["nacos_port"]
    namespace_name=program_info_dict["nacos_config"]["nacos_namespace"]

    nacos_addr=f"http:{nacos_host}:{nacos_port}"
    namespace_path="/nacos/v1/console/namespaces"

    # 创建namespace
    get_namespace_url=f"{nacos_addr}{namespace_path}"
    result=requests.get(get_namespace_url)
    if result.status_code==200:
        for namespace_dict in result.json()["data"]:
            if namespace_dict["namespace"] == namespace_name:
                break
        else:
            namespace_data={
                    "customNamespaceId": namespace_name, 
                    "namespaceName": namespace_name
                    }
            create_namespace_url=f"{nacos_addr}{namespace_path}"
            result=requests.post(create_namespace_url, data=namespace_data)
            if result.status_code == 200:
                log.logger.info(f"已创建namespace: {namespace_name}")
            else
                log.logger.error(f"创建namespace失败: {result.status_code}")
                return error_code
    else:
        log.logger.error(f"无法查询namespace: {result.status_code}")
        return error_code

    # 创建配置文件
    configs_path="/nacos/v1/cs/configs"

    db_type=program_info_dict["db_type"].lower()
    db_host=program_info_dict[f"{db_type}_config"]["db_host"]
    db_port=program_info_dict[f"{db_type}_config"]["db_port"]
    db_name=program_info_dict[f"{db_type}_config"]["db_name"]
    db_user=program_info_dict[f"{db_type}_config"]["db_user"]
    db_password=program_info_dict[f"{db_type}_config"]["db_password"]
    if db_type=="mysql":
        druids={
                "url": f"jdbc:mysql://{db_host}:{db_port}/{db_name}?zeroDateTimeBehavior=CONVERT_TO_NULL&serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useOldAliasMetadataBehavior=true&useSSL=false", 
                "username": db_user, 
                "password": db_password
                }

    config_dict={
            "server":{
                "port": program_info_dict["port"], 
                "servlet": {
                    "session": {
                        "timeout": "720m"
                        }
                    }
                }, 
            "spring": {
                "datasource": {
                    "monitor": {
                        "loginUsername": "_admin2", 
                        "loginPassword": "dreamsoft"
                        }, 
                    "druids": druids
                    }, 
                "redis": {
                    "host": program_info_dict["redis_config"]["redis_host"], 
                    "port": program_info_dict["redis_config"]["redis_port"], 
                    "password": program_info_dict["redis_config"]["redis_password"], 
                    "database": program_info_dict["redis_config"]["redis_db"], 
                    "jedis": {
                        "pool": {
                            "max-idle": 200, 
                            "min-idle": 10
                            }
                        }
                    }, 
                "servlet": {
                    "multipart": {
                        "max-file-size": "1024MB", 
                        "max-request-size": "1024MB"
                        }
                    }
                }, 
            "dsfa": {
                "session": {
                    "rule": {
                        "valiRepeat": False
                        }
                    }
                }, 
            "dsf": {
                "file": {
                    "upload-virtual-path": program_info_dict["upload_path"]
                    }
                }, 
            "dubbo": {
                "scan": {
                    "base-packages": "com.dsfa"
                    }, 
                "protocol": {
                    "name": "dubbo", 
                    "port": -1
                    }, 
                "registry": "nacos://${spring.cloud.nacos.server-addr}/", 
                "cloud": {
                    "subscribed-services": "${spring.application.name}"
                    }
                }
            }

    group_name=program_info_dict["nacos_config"]["nacos_group"]
    config_type=program_info_dict["nacos_config"]["file-extension"]
    service_name=program_info_dict["nacos_config"]["service_name"]
    config_active=program_info_dict["nacos_config"]["active"]
    if config_active is None or len(config_active.strip())==0:
        data_id=f"{server_dict}.{config_type}"
    else:
        data_id=f"{server_dict}-{config_active}.{config_type}"

    config_data={
            "tenant": namespace_name, 
            "dataId": data_id, 
            "group": group_name, 
            "content": yaml.dump(config_dict), 
            "type": config_type
            }
    create_configs_url=f"{nacos_addr}{configs_path}"
    result=requests.post(create_configs_url, data=config_data)
    if result.status_code==200:
        log.logger.info(f"配置发布成功: {data_id}")
    else:
        log.logger.error(f"配置发布失败: {result.status_code}")
        return error_code

    # 生成启动脚本









    jvm_mem=program_info_dict["jvm_mem"]
    for jar_name in os.listdir(program_dir):
        if jar_name.endswith(".jar"):
            jar=jar_name
            break
    config=["application-prod.yml", "application-prod.properties"]
    for config_file in os.listdir(program_dir):
        if config_file in config:
            config_name=config_file
            break
    start_command=f"cd {program_dir} ; nohup java -Xms{jvm_mem} -Xmx{jvm_mem} -jar {jar} --server.port={port_list[0]} --spring.profiles.active=prod &> jar.log &"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=600):
            flag=2
    else:
        log.logger.error(msg)
        flag=1
    return normal_code

def start():
    """启动
    """
    return_value=normal_code
    jvm_mem=program_info_dict["jvm_mem"]
    for jar_name in os.listdir(program_dir):
        if jar_name.endswith(".jar"):
            jar=jar_name
            break
    config=["application-prod.yml", "application-prod.properties"]
    for config_file in os.listdir(program_dir):
        if config_file in config:
            config_name=config_file
            break
    start_command=f"cd {program_dir} ; nohup java -Xms{jvm_mem} -Xmx{jvm_mem} -jar {jar} --server.port={port_list[0]} --spring.profiles.active=prod &> jar.log &"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=600):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def stop():
    """停止
    """
    return_value=normal_code
    for port in port_list:
        pid=common.find_pid(port)
        log.logger.debug(f"{port=}, {pid=}")
        if pid != 0:
            stop_command=f"kill -9 {pid}"
            log.logger.debug(f"{stop_command=}")
            result, msg=common.exec_command(stop_command)
            if result:
                log.logger.debug(f"检测端口: {port_list=}")
                if not common.port_exist(port_list, exist_or_not=False):
                    return_value=error_code
            else:
                log.logger.error(msg)
                return_value=error_code
        else:
            log.logger.warning(f"{softname}未运行")
            return_value=error_code
    return return_value

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

def heapdump():
    """jvm
    """
    return_value=normal_code
    command=f"jmap -dump:format=b, file=heapdump.dump {pid}"
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=600):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    #located=conf_dict.get("located")
    log=common.Logger({"remote": log_remote_level}, loggger_name="jar")

    program_info_dict=conf_dict[f"{softname}_info"]
    port_list=[program_info_dict["port"]]
    program_dir=program_info_dict['program_dir']

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
