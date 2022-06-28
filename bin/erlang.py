#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, erl_src, erl_dst, erl_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    located=conf_dict.get("located")
    pkg_file=conf_dict["pkg_file"]
    erl_dest=f"{located}/{erl_dst}"
    value, msg=common.install(pkg_file, erl_src, erl_dest, erl_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # 配置
    erl_dir=f"{located}/{erl_dst}"
    erl_sh_context=f"""\
            export ERL_HOME={erl_dir}
            export PATH=$ERL_HOME/bin:$PATH
    """
    config_dict={
            "erl_sh":{
                "config_file": "/etc/profile.d/erl.sh", 
                "config_context": erl_sh_context, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
    result, msg=common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return error_code
    return return_value

def run():
    """运行
    """
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
    return normal_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level})

    func_dict={
            "install": install, 
            "run": run, 
            "start": start, 
            "stop": stop, 
            "monitor": monitor, 
            }
    sys.exit(func_dict[action]())
