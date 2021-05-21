#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, jdk_src, jdk_dst, jdk_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code


def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level})

    flag=0
    # 安装
    if action=="install":
        located=conf_dict.get("located")
        pkg_file=conf_dict["pkg_file"]
        value, msg=common.install(pkg_file, jdk_src, jdk_dst, jdk_pkg_dir, located)
        if not value:
            flag=1
            log.logger.error(msg)
            sys.exit(flag)

        # 配置
        jdk_dir=f"{located}/{jdk_dst}"
        jdk_sh_context=f"""\
                export JAVA_HOME={jdk_dir}
                export PATH=$JAVA_HOME/bin:$PATH
        """
        config_dict={
                "jdk_sh":{
                    "config_file": "/etc/profile.d/jdk.sh", 
                    "config_context": jdk_sh_context, 
                    "mode": "w"
                    }
                }
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
        result, msg=common.config(config_dict)
        if not result:
            log.logger.error(msg)
            flag=1
        sys.exit(flag)

    elif action=="run" or action=="start" or action=="stop":
        sys.exit(flag)

def install():
    """安装
    """
    located=conf_dict.get("located")
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, jdk_src, jdk_dst, jdk_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    # 配置
    jdk_dir=f"{located}/{jdk_dst}"
    jdk_sh_context=f"""\
            export JAVA_HOME={jdk_dir}
            export PATH=$JAVA_HOME/bin:$PATH
    """
    config_dict={
            "jdk_sh":{
                "config_file": "/etc/profile.d/jdk.sh", 
                "config_context": jdk_sh_context, 
                "mode": "w"
                }
            }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
    result, msg=common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return error_code
    return normal_code

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
    return activated_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, loggger_name="jdk")

    func_dict={
            "install": install, 
            "run": run, 
            "start": start, 
            "stop": stop, 
            "monitor": monitor, 
            }
    sys.exit(func_dict[action]())
