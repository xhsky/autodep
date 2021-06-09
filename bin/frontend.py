#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, tarfile
from libs import common
from libs.env import log_remote_level, backup_dir, backup_abs_file_format, \
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
    #backup_file_name=f"{backup_version}_{softname}.tar.gz"
    backup_abs_file=backup_abs_file_format.format(backup_dir=backup_dir, backup_version=backup_version, softname=softname)
    try:
        os.makedirs(backup_dir, exist_ok=1)
        with tarfile.open(backup_abs_file, "w:gz", encoding="utf8") as tar:
            tar.add(frontend_dir)
        return normal_code
    except Exception as e:
        log.logger.error(str(e))
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

