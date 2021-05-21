#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, rocketmq_src, rocketmq_dst, rocketmq_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def config_jvm(file_, jvm_mem, log):
    """
    配置jvm
    """
    with open(file_, "r", encoding="utf8") as f_r:
        text=f_r.readlines()
        for line_index, line in enumerate(text):
            if " -server -Xms" in line:
                line_list=line.split()
                for option_index, option in enumerate(line_list):
                    if option.startswith("-Xms"):
                        line_list[option_index]=f"-Xms{jvm_mem}"
                    if option.startswith("-Xmx"):
                        line_list[option_index]=f"-Xmx{jvm_mem}"
                    if option.startswith("-Xmn"):
                        # 判断单位是G还是GB
                        if jvm_mem[-2].isalpha():
                            mem=int(jvm_mem[:-2])
                            unit=jvm_mem[-2:]
                        else:
                            mem=int(jvm_mem[:-1])
                            unit=jvm_mem[-1]
                            xmn_mem=int(mem/2)
                            if xmn_mem==0:
                                xmn_mem=500
                                unit="m"
                        if option.endswith('\"'):
                                unit=f"{unit}\""
                        line_list[option_index]=f"-Xmn{xmn_mem}{unit}"
                line=" ".join(line_list)
                log.logger.debug(f"jvm_str: {line}")
                text[line_index]=f"{line}\n"
        with open(file_, "w", encoding="utf8") as f_w:
            f_w.writelines(text)

def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    rocketmq_dir=f"{located}/{rocketmq_dst}"
    rocketmq_info_dict=conf_dict["rocketmq_info"]

    log=common.Logger({"remote": log_remote_level}, loggger_name="rocketmq")

    namesrv_port=rocketmq_info_dict["port"].get("namesrv_port")
    fast_remote_port=rocketmq_info_dict["port"].get("fast_remote_port")
    remote_port=rocketmq_info_dict["port"].get("remote_port")
    ha_port=rocketmq_info_dict["port"].get("ha_port")
    namesrv_port_list=[namesrv_port]
    broker_port_list=[
            fast_remote_port, 
            remote_port, 
            ha_port
            ]

    flag=0
    # 安装
    if action=="install":
        pkg_file=conf_dict["pkg_file"]
        value, msg=common.install(pkg_file, rocketmq_src, rocketmq_dst, rocketmq_pkg_dir, located)
        if not value:
            log.logger.error(msg)
            flag=1
            sys.exit(flag)
            return 

        log_file_list=[
                f"{rocketmq_dir}/conf/logback_namesrv.xml", 
                f"{rocketmq_dir}/conf/logback_broker.xml", 
                f"{rocketmq_dir}/conf/logback_tools.xml" 
                ]
        store_dir={
                "storePathRootDir": f"{rocketmq_dir}/store", 
                "storePathCommitLog": f"{rocketmq_dir}/store/commitlog", 
                "storePathConsumerQueue": f"{rocketmq_dir}/store/consumequeue", 
                "storePathIndex": f"{rocketmq_dir}/store/index"
                }
        # 配置
        ## 建立存储目录
        for key in store_dir:
            try:
                dir_=store_dir[key]
                log.logger.debug(f"建立目录: {dir_}")
                os.makedirs(dir_, exist_ok=1)
            except Exception as e:
                log.logger.error(f"无法建立{dir_}目录: {str(e)}")
                sys.exit(1)

        namesrv_mem=rocketmq_info_dict.get("namesrv_mem")
        broker_mem=rocketmq_info_dict.get("broker_mem")
        jvm_dict={
                f"{rocketmq_dir}/bin/runserver.sh": namesrv_mem, 
                f"{rocketmq_dir}/bin/runbroker.sh": broker_mem
                }
        ## 配置jvm
        for jvm_file in jvm_dict:
            jvm_mem=jvm_dict[jvm_file]
            log.logger.debug(f"修改jvm: {jvm_file}:{jvm_mem}")
            config_jvm(jvm_file, jvm_mem, log)
        ## 配置日志目录
        for log_file in log_file_list:
            command=f"sed -i 's#${{user.home}}#{rocketmq_dir}#' {log_file}"
            log.logger.debug(f"修改日志目录: {command}")
            result, msg=common.exec_command(command)
            if not result:
                log.logger.error(msg)
                flag=1
        ## 修改配置文件
        cluster_name=rocketmq_info_dict.get("cluster_name")
        broker_name=rocketmq_info_dict.get("replica_name")
        replica_role=rocketmq_info_dict.get("replica_role").lower()
        if replica_role=="master":
            broker_id=0
            broker_role="ASYNC_MASTER"
        elif replica_role=="slave":
            broker_id=1
            broker_role="SLAVE"
        members_list=";".join(rocketmq_info_dict.get("namesrvs"))

        ## 添加启动脚本, 原脚本无法远程后台启动
        start_sh_text=f"""\
                #!/bin/bash
                # sky

                service_type=$1

                if [ $service_type == 'namesrv' ]; then
                    nohup bash ./bin/mqnamesrv -c conf/nameserver.conf &> namesrv.log &
                elif [ $service_type == 'broker' ]; then
                    nohup bash ./bin/mqbroker -c conf/broker.conf &> broker.log &
                fi
        """
        start_sh_file=f"{rocketmq_dir}/bin/start.sh"

        namesrv_config_text=f"""\
                rocketmqHome={rocketmq_dir}
                listenPort={namesrv_port}
        """
        namesrv_config_file=f"{rocketmq_dir}/conf/nameserver.conf"

        broker_config_text=f"""\
                brokerClusterName={cluster_name}
                brokerName={broker_name}
                brokerId={broker_id}
                listenPort={remote_port}
                haListenPort={ha_port}
                namesrvAddr={members_list}
                deleteWhen=04
                fileReservedTime=48
                brokerRole={broker_role}
                flushDiskType=ASYNC_FLUSH

                storePathRootDir={store_dir['storePathRootDir']}
                storePathCommitLog={store_dir['storePathCommitLog']}
                storePathConsumerQueue={store_dir['storePathConsumerQueue']}
                storePathIndex={store_dir['storePathIndex']}
                mapedFileSizeCommitLog=1G
            """
        broker_config_file=f"{rocketmq_dir}/conf/broker.conf"

        rocketmq_sh_text=f"""\
                export ROCKETMQ_HOME={rocketmq_dir}
                export PATH=$ROCKETMQ_HOME/bin:$PATH
        """
        config_dict={
                "namesrv_config": {
                    "config_file": namesrv_config_file, 
                    "config_context": namesrv_config_text, 
                    "mode": "w"
                    }, 
                "broker_config":{
                    "config_file": broker_config_file, 
                    "config_context": broker_config_text, 
                    "mode": "w"
                    }, 
                "rocketmq_sh":{
                    "config_file": "/etc/profile.d/rocketmq.sh", 
                    "config_context": rocketmq_sh_text, 
                    "mode": "w"
                    }, 
                "start_sh":{
                    "config_file": start_sh_file, 
                    "config_context": start_sh_text, 
                    "mode": "w"
                    }
                }
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
        result, msg=common.config(config_dict)
        if result:
            pass
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)
    elif action=="run" or action=="start":
        namesrv_command=f"cd {rocketmq_dir} && bash ./bin/start.sh namesrv" 
        broker_command=f"cd {rocketmq_dir} && bash ./bin/start.sh broker" 

        log.logger.debug(f"{namesrv_command=}")
        result, msg=common.exec_command(namesrv_command)
        if result:
            log.logger.debug(f"检测端口: {namesrv_port_list=}")
            if not common.port_exist(namesrv_port_list):
                flag=2
            else:
                log.logger.debug(f"{broker_command=}")
                result, msg=common.exec_command(broker_command)
                if result:
                    log.logger.debug(f"检测端口: {broker_port_list=}")
                    if not common.port_exist(broker_port_list):
                        flag=2
                else:
                    log.logger.error(msg)
                    flag=1
        else:
            log.logger.error(msg)
            flag=1
        sys.exit(flag)
    elif action=="stop":
        namesrv_command=f"cd {rocketmq_dir} && bash bin/mqshutdown namesrv" 
        broker_command=f"cd {rocketmq_dir} && bash bin/mqshutdown broker" 

        log.logger.debug(f"{namesrv_command=}")
        result, msg=common.exec_command(namesrv_command)
        if result:
            log.logger.debug(f"检测端口: {namesrv_port_list=}")
            if not common.port_exist(namesrv_port_list, exist_or_not=False):
                flag=2
            else:
                log.logger.debug(f"{broker_command=}")
                result, msg=common.exec_command(broker_command)
                if result:
                    log.logger.debug(f"检测端口: {broker_port_list=}")
                    if not common.port_exist(broker_port_list, exist_or_not=False):
                        flag=2
                else:
                    log.logger.error(msg)
                    flag=1
        else:
            log.logger.error(msg)
            flag=1
        sys.exit(flag)

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, rocketmq_src, rocketmq_dst, rocketmq_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    log_file_list=[
            f"{rocketmq_dir}/conf/logback_namesrv.xml", 
            f"{rocketmq_dir}/conf/logback_broker.xml", 
            f"{rocketmq_dir}/conf/logback_tools.xml" 
            ]
    store_dir={
            "storePathRootDir": f"{rocketmq_dir}/store", 
            "storePathCommitLog": f"{rocketmq_dir}/store/commitlog", 
            "storePathConsumerQueue": f"{rocketmq_dir}/store/consumequeue", 
            "storePathIndex": f"{rocketmq_dir}/store/index"
            }
    # 配置
    ## 建立存储目录
    for key in store_dir:
        try:
            dir_=store_dir[key]
            log.logger.debug(f"建立目录: {dir_}")
            os.makedirs(dir_, exist_ok=1)
        except Exception as e:
            log.logger.error(f"无法建立{dir_}目录: {str(e)}")
            return error_code

    namesrv_mem=rocketmq_info_dict.get("namesrv_mem")
    broker_mem=rocketmq_info_dict.get("broker_mem")
    jvm_dict={
            f"{rocketmq_dir}/bin/runserver.sh": namesrv_mem, 
            f"{rocketmq_dir}/bin/runbroker.sh": broker_mem
            }
    ## 配置jvm
    for jvm_file in jvm_dict:
        jvm_mem=jvm_dict[jvm_file]
        log.logger.debug(f"修改jvm: {jvm_file}:{jvm_mem}")
        config_jvm(jvm_file, jvm_mem, log)
    ## 配置日志目录
    for log_file in log_file_list:
        command=f"sed -i 's#${{user.home}}#{rocketmq_dir}#' {log_file}"
        log.logger.debug(f"修改日志目录: {command}")
        result, msg=common.exec_command(command)
        if not result:
            log.logger.error(msg)
            return_value=error_code
    ## 修改配置文件
    cluster_name=rocketmq_info_dict.get("cluster_name")
    broker_name=rocketmq_info_dict.get("replica_name")
    replica_role=rocketmq_info_dict.get("replica_role").lower()
    if replica_role=="master":
        broker_id=0
        broker_role="ASYNC_MASTER"
    elif replica_role=="slave":
        broker_id=1
        broker_role="SLAVE"
    members_list=";".join(rocketmq_info_dict.get("namesrvs"))

    ## 添加启动脚本, 原脚本无法远程后台启动
    start_sh_text=f"""\
            #!/bin/bash
            # sky

            service_type=$1

            if [ $service_type == 'namesrv' ]; then
                nohup bash ./bin/mqnamesrv -c conf/nameserver.conf &> namesrv.log &
            elif [ $service_type == 'broker' ]; then
                nohup bash ./bin/mqbroker -c conf/broker.conf &> broker.log &
            fi
    """
    start_sh_file=f"{rocketmq_dir}/bin/start.sh"

    namesrv_config_text=f"""\
            rocketmqHome={rocketmq_dir}
            listenPort={namesrv_port}
    """
    namesrv_config_file=f"{rocketmq_dir}/conf/nameserver.conf"

    broker_config_text=f"""\
            brokerClusterName={cluster_name}
            brokerName={broker_name}
            brokerId={broker_id}
            listenPort={remote_port}
            haListenPort={ha_port}
            namesrvAddr={members_list}
            deleteWhen=04
            fileReservedTime=48
            brokerRole={broker_role}
            flushDiskType=ASYNC_FLUSH

            storePathRootDir={store_dir['storePathRootDir']}
            storePathCommitLog={store_dir['storePathCommitLog']}
            storePathConsumerQueue={store_dir['storePathConsumerQueue']}
            storePathIndex={store_dir['storePathIndex']}
            mapedFileSizeCommitLog=1G
        """
    broker_config_file=f"{rocketmq_dir}/conf/broker.conf"

    rocketmq_sh_text=f"""\
            export ROCKETMQ_HOME={rocketmq_dir}
            export PATH=$ROCKETMQ_HOME/bin:$PATH
    """
    config_dict={
            "namesrv_config": {
                "config_file": namesrv_config_file, 
                "config_context": namesrv_config_text, 
                "mode": "w"
                }, 
            "broker_config":{
                "config_file": broker_config_file, 
                "config_context": broker_config_text, 
                "mode": "w"
                }, 
            "rocketmq_sh":{
                "config_file": "/etc/profile.d/rocketmq.sh", 
                "config_context": rocketmq_sh_text, 
                "mode": "w"
                }, 
            "start_sh":{
                "config_file": start_sh_file, 
                "config_context": start_sh_text, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        pass
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    namesrv_command=f"cd {rocketmq_dir} && bash ./bin/start.sh namesrv" 
    broker_command=f"cd {rocketmq_dir} && bash ./bin/start.sh broker" 

    log.logger.debug(f"{namesrv_command=}")
    result, msg=common.exec_command(namesrv_command)
    if result:
        log.logger.debug(f"检测端口: {namesrv_port_list=}")
        if not common.port_exist(namesrv_port_list):
            return_value=error_code
        else:
            log.logger.debug(f"{broker_command=}")
            result, msg=common.exec_command(broker_command)
            if result:
                log.logger.debug(f"检测端口: {broker_port_list=}")
                if not common.port_exist(broker_port_list):
                    return_value=error_code
            else:
                log.logger.error(msg)
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
    namesrv_command=f"cd {rocketmq_dir} && bash bin/mqshutdown namesrv" 
    broker_command=f"cd {rocketmq_dir} && bash bin/mqshutdown broker" 

    log.logger.debug(f"{namesrv_command=}")
    result, msg=common.exec_command(namesrv_command)
    if result:
        log.logger.debug(f"检测端口: {namesrv_port_list=}")
        if not common.port_exist(namesrv_port_list, exist_or_not=False):
            return_value=error_code
        else:
            log.logger.debug(f"{broker_command=}")
            result, msg=common.exec_command(broker_command)
            if result:
                log.logger.debug(f"检测端口: {broker_port_list=}")
                if not common.port_exist(broker_port_list, exist_or_not=False):
                    return_value=error_code
            else:
                log.logger.error(msg)
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
    rocketmq_dir=f"{located}/{rocketmq_dst}"
    rocketmq_info_dict=conf_dict["rocketmq_info"]

    log=common.Logger({"remote": log_remote_level}, loggger_name="rocketmq")

    namesrv_port=rocketmq_info_dict["port"].get("namesrv_port")
    fast_remote_port=rocketmq_info_dict["port"].get("fast_remote_port")
    remote_port=rocketmq_info_dict["port"].get("remote_port")
    ha_port=rocketmq_info_dict["port"].get("ha_port")
    namesrv_port_list=[namesrv_port]
    broker_port_list=[
            fast_remote_port, 
            remote_port, 
            ha_port
            ]
    port_list=namesrv_port_list+broker_port_list

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
