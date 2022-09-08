#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, pexpect, time
from libs import common
from libs.env import log_remote_level, test_sql_file, normal_code, error_code, activated_code, stopped_code, abnormal_code

def test():
    """测试
    """
    return_value=normal_code
    result_value="0"
    if softname=="dameng":
        sql_text="""\
        set HEA off;
        set LINESHOW off;
        set TIMING off;
        select 0;
        exit;
        """
        config_dict={
                "test_config": {
                    "config_file": sql_file,
                    "config_context": sql_text,
                    "mode": "w"
                    }
                }
        result, msg=common.config(config_dict)
        if result:
            test_command=f"su -l {system_user} -c 'disql -S -L {dba_user}/{dba_password} \`{sql_file}'"
        else:
            log.logger.error(msg)
            return error_code
    elif softname=="kingbase":
        test_command=f"su -l {system_user} -c 'ksql -V'"
    log.logger.debug(f"test db comand: {test_command}")
    result, msg=common.exec_command(test_command)
    if result and msg.strip()==result_value:
        return normal_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def install():
    """安装: 已安装, 无需安装
    """
    return normal_code

def run():
    """运行
    """
    business_user=localization_info_dict["business_user"]
    business_password=localization_info_dict["business_password"]
    return_value=normal_code
    log.logger.debug(f"创建业务账号...")
    if softname=="dameng":
        #select distinct object_name from all_objects where object_type = 'sch' and owner='user1';
        create_sql_template="create user %s identified by %s;\ngrant dba to %s;"
        create_command=f"su -l {system_user} -c 'disql -S -L {dba_user}/{dba_password} \`{sql_file}'"
        exit_sql="exit;"
        create_sql_list=["set TIMING off;"]
        for user, password in zip(business_user, business_password):
            create_sql=create_sql_template % (user, password, user)
            create_sql_list.append(create_sql)
        else:
            create_sql_list.append(exit_sql)

        config_dict={
                "create_config":{
                    "config_file": sql_file,
                    "config_context": "\n".join(create_sql_list),
                    "mode": "w"
                    }
                }
        result, msg=common.config(config_dict)
        if not result:
            log.logger.error(msg)
            return error_code
        log.logger.debug(f"create user command: {create_command}")
        result, msg=common.exec_command(create_command, timeout=600)
        if result:
            if "错误" in msg or "error" in msg.lower():
                log.logger.error(msg)
                return_value=error_code
        else:
            log.logger.error(msg)
            return_value=error_code
        return return_value
    elif softname=="kingbase":
        for user, password in zip(business_user, business_password):
            child = pexpect.spawn(f"su -l {system_user} -c 'createuser -U{dba_user} -p{db_port} -P {user}'", maxread=10000,
                                  timeout=120)
            for i in range(13):
                index = child.expect(["Enter password for new role:", 'Enter it again:', pexpect.TIMEOUT, pexpect.EOF])
                if index == 0:
                    child.sendline(password)
                elif index == 1:
                    child.sendline(password)
            time.sleep(10)
            create_command=f'''su -l {system_user} -c "ksql -U{dba_user} -p{db_port} -c'\du' -dtest | grep {user}"'''
            result, msg = common.exec_command(create_command, timeout=600)
            if result:
                if user not in msg:
                    log.logger.error(f"{user}用户未创建成功")
                    return_value = error_code
            else:
                log.logger.error(msg)
                return_value = error_code
            return return_value
def start():
    """启动
    """
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
    # softname="kingbase"
    # action="run"
    # conf_json = """
    # {
    #     "software": ["kingbase", "program_graduate_sql"],
    #     "located": "/dream/",
    #     "ip": "127.0.0.1",
    #     "kingbase_info": {
    # 	  "business_user": ["dream1"],
    #       "business_password": ["DreamSoft_123"],
    #       "system_user": "kingbase",
    #       "db_host": "127.0.0.1",
    #       "dba_user": "system",
    #       "dba_password": "dreamsoft",
    #       "db_port": 54321,
    #       "start_command": "su -l kingbase 'sys_ctl start -D /data/kingbase/data/'",
    #       "stop_command": "su -l kingbase 'sys_ctl stop -D /data/kingbase/data'"
    #     },
    #     "program_graduate_sql_info": {
    # 	  "db_type": "kingbase",
    #       "db_port": 54321,
    #       "sql_dir": "/dream/sql" ,
    #       "db_type": "kingbase",
    #       "to_user": "dream1",
    #       "db_name": "db3"
    #     }
    # }
    #     """
    conf_dict=json.loads(conf_json)

    log=common.Logger({"remote": log_remote_level}, loggger_name=softname)
    localization_info_dict=conf_dict.get(f"{softname}_info")
    db_port=localization_info_dict["db_port"]
    port_list=[
            db_port
            ]
    sql_file=test_sql_file % softname
    system_user = localization_info_dict["system_user"]
    dba_user = localization_info_dict["dba_user"]
    if softname=="dameng":
        dba_password=localization_info_dict["dba_password"]
        db_port=localization_info_dict["db_port"]
        start_command=localization_info_dict["start_command"]
        stop_command=localization_info_dict["stop_command"]

    if action=="test":
        sys.exit(test())
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
