#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, requests, yaml, tarfile
from libs import common
from libs.env import log_remote_level, program_sh_name, backup_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

"""
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
"""

def dict_to_yaml_file(config_dict, config_file):
    """生成将dict转为yaml文件
    """
    try: 
        with open(config_file, "w", encoding="utf8") as f:
            yaml.safe_dump(config_dict, f)
        return True, config_file
    except Exception as e:
        return False, str(e)

def generate_local_config():
    """在本地生成一份配置文件
    """
    db_type=program_info_dict["db_type"].lower()
    db_host=program_info_dict[f"{db_type}_config"]["db_host"]
    db_port=program_info_dict[f"{db_type}_config"]["db_port"]
    db_name=program_info_dict[f"{db_type}_config"]["db_name"]
    db_user=program_info_dict[f"{db_type}_config"]["db_user"]
    db_password=program_info_dict[f"{db_type}_config"]["db_password"]
    if db_type=="mysql":
        druids=[
                {
                "url": f"jdbc:mysql://{db_host}:{db_port}/{db_name}?zeroDateTimeBehavior=CONVERT_TO_NULL&serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useOldAliasMetadataBehavior=true&useSSL=false", 
                "username": db_user, 
                "password": db_password
                }
                ]
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
                }
            }
    if not (softname.endswith("gateway") and softname.startswith("program")):
        config_dict["dsfa"]={
                "session": {
                    "rule": {
                        "valiRepeat": False
                        }
                    }
                }
        config_dict["dsf"]={
                "file": {
                    "upload-virtual-path": program_info_dict["upload_path"]
                    }
                }
        config_dict["dubbo"]={
                "scan": {
                    "base-packages": "com.dsfa"
                    }, 
                "protocol": {
                    "name": "dubbo", 
                    "port": -1
                    }, 
                "registry": {
                    "address": "nacos://${spring.cloud.nacos.server-addr}/"
                    }, 
                "cloud": {
                    "subscribed-services": "${spring.application.name}"
                    }
                }

    if program_info_dict.get("routes"):
        config_dict["spring"]["cloud"]={
                "gateway": {
                    "discovery": {
                        "locator": {
                            "enabled": True, 
                            "filters": ["StripPrefix=1"]
                            }
                        }, 
                    "routes": program_info_dict.get("routes")
                    }
                }

    result, msg=dict_to_yaml_file(config_dict, config_file)
    if result:
        return True
        log.logger.debug(f"生成可读配置文件: {msg}")
    else:
        log.logger.error(f"无法生成可读配置文件: {msg}")
        return False

def generate_sh(jar_file):
    """生成控制脚本
    """
    nacos_addr=f"{nacos_host}:{nacos_port}"
    jvm_mem=program_info_dict["jvm_mem"]
    #jar_file=f"{program_dir}/{pkg_file.split('/')[-1]}"
    jar_file=f"{program_dir}/{jar_file}"
    log_file=f"{program_dir}/{service_name}.log"
    program_sh_text=f"""\
            #!/bin/bash
            # sky

            action=$1
            jar_file={jar_file}
            jar_name=`echo $jar_file | rev | cut -d "/" -f 1 | rev`
            if [ -z "$1" ]; then
              echo "Usage: $0 start|stop"
              exit {error_code}
            elif [ "$action" == "start" ]; then
              jvm_mem={jvm_mem}
              nacos_addr={nacos_addr}
              nacos_namespace={namespace_name}
              nacos_group={group_name}
              nacos_config_file_extension={config_file_type}
              nacos_application_name={service_name}         # 须同jar_name配套
              nacos_profiles_active={config_active}         # 须同jar_name配套
              accept_count=1000
              threads=500
              max_connections=8192


              log_file={log_file}

              nohup java -jar -Xms${{jvm_mem}} -Xmx${{jvm_mem}} ${{jar_file}} \\
                --spring.cloud.nacos.server-addr=$nacos_addr \\
                --spring.cloud.nacos.config.namespace=$nacos_namespace \\
                --spring.cloud.nacos.config.group=$nacos_group \\
                --spring.cloud.nacos.config.file-extension=$nacos_config_file_extension \\
                --spring.cloud.nacos.config.enabled=True \\
                --spring.cloud.nacos.discovery.enabled=True \\
                --spring.cloud.nacos.discovery.namespace=$nacos_namespace \\
                --spring.cloud.nacos.discovery.group=$nacos_group \\
                --spring.application.name=$nacos_application_name \\
                --spring.profiles.active=$nacos_profiles_active \\
                --server.tomcat.accept-count=$accept_count \\
                --server.tomcat.min-spare-threads=$threads \\
                --server.tomcat.max-threads=$threads \\
                --server.tomcat.max-connections=$max_connections \\
                &> $log_file &
              echo "$jar_name启动中, 详细请查看日志文件($log_file)."
              exit {normal_code}
            elif [ "$action" == "stop" ]; then
              N=0
              while : ;do
                N=$((N+1))
                Pid=`ps ax | grep java | grep "$jar_name" |  grep -v grep | awk '{{print $1}}'`
                if [ -z "$Pid" ]; then
                  if [ $N == 1 ]; then
                    echo "${{jar_name}}未运行. "
                    exit {stopped_code}
                  else
                    echo "${{jar_name}}已关闭."
                    exit {normal_code}
                  fi
                else
                  if [ $N == 1 ]; then
                    echo "Pid: $Pid"
                    echo "${{jar_name}}关闭中..."
                    kill $Pid
                  fi

                  if [ $N == 30 ]; then
                    kill -9 $Pid
                  fi
                fi
                sleep 1
              done
            else
              echo "Usage: $0 start|stop"
            fi
    """
    config_dict={
            "program_sh": {
                "config_file": program_sh_file, 
                "config_context": program_sh_text, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {program_sh_file}")
    result, msg=common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return False
    return True

def install():
    """安装
    """
    pkg_file=conf_dict["pkg_file"]
    if pkg_file.endswith(".tar.gz"):
        value, msg=common.install(pkg_file, "tar.gz", None, None, program_dir)
        if not value:
            log.logger.error(msg)
            return error_code
        for file_ in os.listdir(program_dir):
            if file_.endswith(".jar"):
                jar_file=file_
                break
        else:
            log.logger.error(f"jar文件不存在")
            return error_code

        if os.path.exists(config_file):
            log.logger.debug(f"已存在可读配置文件: {config_file}")
        else:
            #result=generate_local_config()
            #if not result:
            #    return error_code
            log.logger.error(f"{config_file}不存在")
            return error_code
        if os.path.exists(program_sh_file):
            log.logger.debug(f"已存在控制脚本: {program_sh_file}")
        else:
            result=generate_sh(jar_file)
            if not result:
                return error_code
            #log.logger.error(f"{program_sh_file}不存在")
            #return error_code
    #elif pkg_file.endswith(".jar"):
    #    value, msg=common.install(pkg_file, "jar", None, None, program_dir)
    #    if not value:
    #        log.logger.error(msg)
    #        return error_code
    #    result=generate_local_config()
    #    if not result:
    #        return error_code
    #    result=generate_sh(pkg_file)
    #    if not result:
    #        return error_code
    else:
        log.logger.error(f"未知文件后缀: {pkg_file}")
        return error_code
    return normal_code

def run():
    """运行
    """
    # 创建namespace
    namespace_path="/nacos/v1/console/namespaces"
    get_namespace_url=f"{nacos_addr_url}{namespace_path}"
    try: 
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
                create_namespace_url=f"{nacos_addr_url}{namespace_path}"
                result=requests.post(create_namespace_url, data=namespace_data)
                if result.status_code == 200:
                    log.logger.info(f"创建namespace: {namespace_name}")
                else:
                    log.logger.error(f"创建namespace失败: {result.status_code}")
                    return error_code
        else:
            log.logger.error(f"无法查询namespace: {result.status_code}")
            return error_code
    except Exception as e:
        log.logger.error(f"无法连接nacos: {str(e)}")
        return error_code

    # 发布配置
    with open(config_file, "r", encoding="utf8") as f:
        config_yaml_str=f.read()
    config_data={
            "tenant": namespace_name, 
            "dataId": data_id, 
            "group": group_name, 
            "content": config_yaml_str, 
            "type": config_file_type
            }
    create_configs_url=f"{nacos_addr_url}{configs_path}"
    try:
        result=requests.post(create_configs_url, data=config_data)
        if result.status_code==200:
            log.logger.info(f"配置发布成功: {data_id}")
        else:
            log.logger.error(f"配置发布失败: {result.status_code}")
            return error_code
    except Exception as e:
        log.logger.error(f"无法连接nacos: {str(e)}")
        return error_code

    # 启动
    return start()

def start():
    """启动
    """
    return_value=normal_code
    start_command=f"bash -lc 'cd {program_dir} ; bash {program_sh_file} start'" 
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
    stop_command=f"bash -lc 'cd {program_dir} ; bash {program_sh_file} stop'"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command)
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

def backup():
    """program备份
    """
    # 获取最新配置并写入文件
    log.logger.info("备份配置文件...")
    config_data={
            "tenant": namespace_name, 
            "dataId": data_id, 
            "group": group_name
            }
    get_configs_url=f"{nacos_addr_url}{configs_path}"
    try:
        result=requests.get(get_configs_url, params=config_data)
        if result.status_code==200:
            log.logger.debug(f"配置获取成功: {data_id}")
            config_dict={
                    "config_sh": {
                        "config_file": config_file, 
                        "config_context": result.text, 
                        "mode": "w"
                        }
                    }
            log.logger.debug(f"写入配置文件: {config_file}")
            result, msg=common.config(config_dict)
            if not result:
                log.logger.error(msg)
                return error_code
        else:
            log.logger.error(f"配置获取失败: {result.status_code}: {result.text}")
            return error_code
    except Exception as e:
        log.logger.error(f"无法连接nacos: {str(e)}")
        return error_code

    log.logger.info("备份代码...")
    backup_version=conf_dict["backup_version"]
    backup_file_list=[]
    for backup_file in os.listdir(program_dir):
        if backup_file.endswith(".log") or backup_file.endswith(".bak"):
            pass
        else:
            backup_file_list.append(os.path.basename(backup_file))
    result, msg=common.tar_backup(backup_version, backup_dir, softname, program_dir, [])
    if result:
        return normal_code
    else:
        log.logger.error(msg)
        return error_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    #located=conf_dict.get("located")
    log=common.Logger({"remote": log_remote_level}, loggger_name="jar")

    program_info_dict=conf_dict[f"{softname}_info"]
    port_list=[program_info_dict["port"]]
    program_dir=program_info_dict['program_dir']

    nacos_host=program_info_dict["nacos_config"]["nacos_host"]
    nacos_port=program_info_dict["nacos_config"]["nacos_port"]
    namespace_name=program_info_dict["nacos_config"]["nacos_namespace"]
    group_name=program_info_dict["nacos_config"]["nacos_group"]

    service_name=program_info_dict["nacos_config"]["service_name"]
    config_active=program_info_dict["nacos_config"]["active"]
    config_file_type=program_info_dict["nacos_config"]["file-extension"]
    if config_active is None or len(config_active.strip())==0:
        data_id=f"{service_name}.{config_file_type}"
    else:
        data_id=f"{service_name}-{config_active}.{config_file_type}"
    #config_file=f"{program_dir}/{data_id}"
    config_file=f"{program_dir}/application.{config_file_type}"

    nacos_addr_url=f"http://{nacos_host}:{nacos_port}"
    configs_path="/nacos/v1/cs/configs"
    program_sh_file=f"{program_dir}/{program_sh_name}"

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
    elif action=="backup":
        sys.exit(backup())
    else:
        sys.exit(error_code)
