#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, normal_code, error_code, activated_code, stopped_code, abnormal_code

def test():
    """运行
    """
    return_value=normal_code
    if softname=="dameng":
        test_command=f"""su -l {system_user} -c 'disql -S -L {dba_uesr}/{dba_password} -e "select 0"'"""
    log.logger.debug(f"{test_command=}")
    result, msg=common.exec_command(test_command)
    if result:
        log.logger.error(msg)
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    #init_command=f"{mysql_dir}/bin/mysqld --initialize --user={mysql_user} --datadir={mysql_dir}/{my_data}"
    init_command=f"{mysql_dir}/bin/mysqld --initialize --user={mysql_user}"
    log.logger.debug(f"初始化中: {init_command=}")
    result, msg=common.exec_command(init_command, timeout=600)
    if result:
        try:
            log.logger.debug("获取随机密码")
            with open(f"{mysql_dir}/{my_logs}/mysqld.log", "r") as f:
                for i in f.readlines():
                    if "temporary password" in i:
                        pass_line=i.split(" ")
                        init_password=pass_line[-1].strip()
                        log.logger.debug(f"{init_password=}")
                        break
        except Exception as e:
            log.logger.error(str(e))
            sys.exit(error_code)

        start_command=f"systemctl start mysqld"
        log.logger.debug(f"{start_command=}")
        result, msg=common.exec_command(start_command, timeout=600)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if common.port_exist(port_list):
                return_value=init(db_info_dict, mysql_dir, init_password, cluster_info_dict, role, log)
            else:
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
    start_command=f"systemctl start mysqld"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command, timeout=600)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return error_code
    else:
        log.logger.error(msg)
        return error_code
    return normal_code

def stop():
    """停止
    """
    stop_command=f"systemctl stop mysqld"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command, timeout=600)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return error_code
    else:
        log.logger.error(msg)
        return error_code
    return normal_code

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)

    log=common.Logger({"remote": log_remote_level}, loggger_name=softname)
    localization_info_dict=conf_dict.get(f"{softname}_info")
    port_list=[
            mysql_port
            ]
    if softname=="dameng":
        business_user=localization_info_dict["business_user"]
        business_password=localization_info_dict["business_password"]
        system_user=localization_info_dict["system_user"]
        dba_user=localization_info_dict["dba_user"]
        dba_password=localization_info_dict["dba_password"]
        db_port=localization_info_dict["db_port"]
        start_command=localization_info_dict["start_command"]
        stop_command=localization_info_dict["stop_command"]


    if action=="test":
        sys.exit(test())
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
