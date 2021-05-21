#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os
from libs import common
from libs.env import log_remote_level, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=0
    db_tar_file=conf_dict["pkg_file"]
    value, msg=common.install(db_tar_file, None, None, None, located)
    if not value:
        log.logger.error(msg)
        return error_code
    return return_value

def run():
    """运行
    """
    db_type=sql_info_dict["db_type"]
    db_file=os.listdir(sql_dir)[0]
    db_abs_file=os.path.abspath(f"{sql_dir}/{db_file}")
    if db_type.lower()=="mysql":
        db_name=sql_info_dict["db_name"]
        root_password=sql_info_dict["root_password"]
        db_port=sql_info_dict["db_port"]
        source_db_command=f"mysql -uroot -p{root_password} -P {db_port} {db_name} < {db_abs_file}"
        log.logger.debug(f"{source_db_command=}")
        log.logger.info(f"{softname}: 数据导入中, 请稍后...")
        result, msg=common.exec_command(source_db_command, timeout=3600)
        if result:
            if os.path.exists(db_file):
                log.logger.info("清理数据包...")
                os.remove(db_file)
            return normal_code
        else:
            log.logger.error(msg)
            return error_code

def start():
    """启动
    """
    return normal_code

def stop():
    """关闭
    """
    return normal_code

def monitor():
    """监控
    """
    return normal_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, logger_name="sql")

    located=conf_dict["located"]
    sql_dir=f"{located}/{softname}"             # 数据文件的上级目录名称必须与其软件名称相同
    sql_info_dict=conf_dict[f"{softname}_info"]

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

