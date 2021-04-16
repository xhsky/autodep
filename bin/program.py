#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os
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
    return normal_code

def run():
    """运行
    """
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
    located=conf_dict.get("located")
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
