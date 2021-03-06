#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import configparser, psutil
from libs import common
from libs.env import log_remote_level, autocheck_src, autocheck_dst, autocheck_pkg_dir, remote_python_exec, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, autocheck_src, autocheck_dst, autocheck_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # 配置
    config=configparser.ConfigParser()
    config["autocheck"]={}
    hostname_command="hostname -s"
    result, msg=common.exec_command(hostname_command)
    log.logger.debug(f"{msg=}")
    if result:
        config["autocheck"]["hostname"]=msg.strip()
    else:
        log.logger.error(msg)
        return error_code

    config["autocheck"]["warning_percent"]="95"
    config["autocheck"]["warning_interval"]="30"
    config["autocheck"]["analysis_interval"]="15"
    config["autocheck"]["keep_days"]="3"

    config["logs"]={}
    config["logs"]["log_file"]="./logs/autocheck.log"
    config["logs"]["log_level"]="info"

    config["host"]={}
    config["host"]["disk_interval"]="300"
    config["host"]["cpu_interval"]="20"
    config["host"]["memory_interval"]="20"
    config["host"]["swap_interval"]="300"
    config["host"]["users_limit"]=""

    config["redis"]={}
    if "redis" in conf_dict["software"]:
        config["redis"]["check"]="1"
        config["redis"]["redis_interval"]="15"
        config["redis"]["password"]=conf_dict["redis_info"]["db_info"]["redis_password"]
        config["redis"]["redis_port"]=str(conf_dict["redis_info"]["db_info"]["redis_port"])
        if conf_dict["redis_info"].get("sentinel_info"):
            config["redis"]["sentinel_port"]=str(conf_dict["redis_info"]["sentinel_info"]["sentinel_port"])
            config["redis"]["sentinel_name"]="mymaster"
    else:
        config["redis"]["check"]="0"

    config["mysql"]={}
    if "mysql" in conf_dict["software"]:
        config["mysql"]["check"]="1"
        config["mysql"]["mysql_interval"]="15"
        config["mysql"]["mysql_port"]=str(conf_dict["mysql_info"]["db_info"]["mysql_port"])
        config["mysql"]["mysql_password"]=conf_dict["mysql_info"]["db_info"]["root_password"]
        config["mysql"]["seconds_behind_master"]="5"
    else:
        config["mysql"]["check"]="0"

    config["oracle"]={}
    if "oracle" in conf_dict["software"]:
        config["oracle"]["check"]="1"
        config["oracle"]["oracle_interval"]="300"
        config["oracle"]["awr_hours"]="24"
    else:
        config["oracle"]["check"]="0"

    config["backup"]={}
    if "backup" in conf_dict["software"]:
        config["backup"]["check"]="1"
        ...
    else:
        config["backup"]["check"]="0"

    if autocheck_info_dict.get("matching_info"):
        pass

    config["notify"]={}
    if autocheck_info_dict.get("warning_info"):
        if autocheck_info_dict["warning_info"].get("mail_info"):
            config["notify"]["mail"]="1"
            config["notify"]["mail_sender"]=autocheck_info_dict["warning_info"]["mail_info"]["mail_sender"]
            config["notify"]["mail_receive"]=",".join(autocheck_info_dict["warning_info"]["mail_info"]["mail_receive"])
            config["notify"]["mail_subject"]=autocheck_info_dict["warning_info"]["mail_info"]["mail_subject"]
        else:
            config["notify"]["mail"]="0"
        if autocheck_info_dict["warning_info"].get("sms_info"):
            config["notify"]["sms"]="1"
            config["notify"]["sms_receive"]=",".join(autocheck_info_dict["warning_info"]["sms_info"]["sms_receive"])
            config["notify"]["sms_subject"]=autocheck_info_dict["warning_info"]["sms_info"]["sms_subject"]
        else:
            config["notify"]["sms"]="0"
    else:
        config["notify"]["mail"]="0"
        config["notify"]["sms"]="0"

    config["send"]={}
    if autocheck_info_dict.get("inspection_info"):
        config["send"]["check"]="1"
        config["send"]["send_time"]=autocheck_info_dict["inspection_info"]["inspection_time"]
        config["send"]["granularity_level"]="10"
        config["send"]["send_sender"]=autocheck_info_dict["inspection_info"]["inspection_sender"]
        config["send"]["send_receive"]=",".join(autocheck_info_dict["inspection_info"]["inspection_receive"])
        config["send"]["send_subject"]=autocheck_info_dict["inspection_info"]["inspection_subject"]
    else:       # 巡检按钮为1, 确保当未配置巡检邮箱时生成巡检报告
        config["send"]["check"]="1"
        config["send"]["send_time"]="18:30"
        config["send"]["granularity_level"]="10"
        config["send"]["send_sender"]="xxx"
        config["send"]["send_receive"]="xxx@dreamdt.cn"
        config["send"]["send_subject"]="xx项目巡检"

    try:
        config_file=f"{autocheck_dir}/conf/autocheck.conf"
        with open(config_file, "w", encoding="utf8") as configfile:
            config.write(configfile)
            log.logger.debug(f"写入配置文件: {config_file}")
    except Exception as e:
        log.logger.debug(f"写入配置文件失败: {str(e)}")
        return error_code
    return normal_code

def run():
    """运行
    """
    command=f"cd {autocheck_dir} ; {remote_python_exec} ./main.py start"
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if result:
        if not os.path.exists(f"{autocheck_dir}/logs/autocheck.pid"):
            return error_code
    else:
        log.logger.error(msg)
        return error_code
    return normal_code

def start():
    """启动
    """
    return run()

def stop():
    """关闭
    """
    command=f"cd {autocheck_dir} ; {remote_python_exec} ./main.py stop"
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
        return error_code
    return normal_code

def monitor():
    """监控
    """
    pid_file=f"{autocheck_dir}/logs/autocheck.pid"
    if os.path.exists(pid_file):
        with open(pid_file, "r", encoding="utf8") as f:
            pid=f.read()
            if pid != '':
                pid=int(pid)
                if psutil.pid_exists(pid):
                    cmdline=",".join(psutil.Process(pid).cmdline())
                    if "python" in cmdline and "main.py" in cmdline:
                        return activated_code
    return stopped_code

def sendmail():
    """发送巡检信息
    """
    command=f"cd {autocheck_dir} ; {remote_python_exec} ./main.py sendmail"
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
        return error_code
    return normal_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict["located"]
    log=common.Logger({"remote": log_remote_level}, loggger_name="autocheck")

    autocheck_dir=f"{located}/{autocheck_dst}"
    autocheck_info_dict=conf_dict["autocheck_info"]

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
    elif action=="sendmail":
        sys.exit(sendmail())
    else:
        sys.exit(error_code)
