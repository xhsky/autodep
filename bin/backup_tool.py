#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, backup_tool_src, backup_tool_dst, backup_tool_pkg_dir, \
        remote_python_exec, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    located=conf_dict.get("located")
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, backup_tool_src, backup_tool_dst, backup_tool_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    # 配置各个备份信息的config文件
    config_dict={}
    crontab_str=""
    type_key_str="type"
    for i in backup_tool_info_dict:
        backup_type_dict=backup_tool_info_dict[i]
        for j in backup_type_dict:
            if j != type_key_str:
                log.logger.debug(f"生成{i}_{j}配置")
                backup_type_dict[j][type_key_str]=backup_type_dict[type_key_str]
                backup_type_dict[j]["keyword"]=j
                file_name=f"{i}_{j}"
                config_file=f"{backup_tool_config_dir}/{file_name}.json"
                config_dict[file_name]={
                        "config_file": config_file, 
                        "config_context": backup_type_dict[j], 
                        "mode": "w", 
                        "type": "json"
                        }
                timing=backup_type_dict[j]["timing"]
                crontab_str=f"{crontab_str}{timing} {remote_python_exec} {backup_tool_dir}/bin/backup.py {config_file}\n"
    else:   # 将各个备份的定时语法写入文件
        log.logger.debug(f"生成crontab配置")
        crontab_list_command="bash -lc 'crontab -l'"
        log.logger.debug(f"{crontab_list_command=}")
        result, msg=common.exec_command(crontab_list_command, timeout=5)
        if result:
            crontab_list_str=msg
        else:
            if msg.strip()=="no crontab for root":
                crontab_list_str=""
            else:
                log.logger.error(msg)
                return error_code

        config_dict["crontab_list"]={
                "config_file": backup_crontab_file,
                "config_context": crontab_list_str,
                "mode": "w"
                }
        config_dict["crontab"]={
                "config_file": backup_crontab_file,
                "config_context": crontab_str,
                "mode": "r+"
                }

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
    result, msg=common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return error_code
    return normal_code

def run():
    """运行
    将备份任务写入crontab
    """
    crontab_command=f"bash -lc 'crontab {backup_crontab_file}'"
    log.logger.debug(f"{crontab_command=}")
    result, msg=common.exec_command(crontab_command, timeout=5)
    if not result:
        log.logger.error(msg)
        return error_code
    return normal_code

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
    return activated_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    log=common.Logger({"remote": log_remote_level}, loggger_name="backup")

    backup_tool_dir=f"{located}/{backup_tool_src}"
    backup_tool_config_dir=f"{backup_tool_dir}/config"
    backup_crontab_file=f"{backup_tool_config_dir}/crontab"
    backup_tool_info_dict=conf_dict[f"{softname}_info"]

    func_dict={
            "install": install, 
            "run": run, 
            "start": start, 
            "stop": stop, 
            "monitor": monitor, 
            }
    sys.exit(func_dict[action]())
