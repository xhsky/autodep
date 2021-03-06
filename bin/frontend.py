#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, tarfile
from libs import common
from libs.env import log_remote_level, backup_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=0
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, "frontend", None, None, frontend_dir)
    if not value:
        log.logger.error(msg)
        return error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    return return_value

def start():
    """启动
    """
    return run()

def stop():
    """关闭
    """
    return_value=normal_code
    return return_value

def monitor():
    """监控
    """
    return_value=normal_code
    return return_value

def backup():
    """备份
    """
    backup_version=conf_dict["backup_version"]
    result, msg=common.tar_backup(backup_version, backup_dir, softname, frontend_dir, [])
    if result:
        return normal_code
    else:
        log.logger.error(msg)
        return error_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, loggger_name="frontend")
    frontend_dir=conf_dict[f"{softname}_info"]["frontend_dir"]

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

