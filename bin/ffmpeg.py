#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    located=conf_dict["located"]
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, located)
    if not value:
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
    log=common.Logger({"remote": log_remote_level}, loggger_name="ffmpeg")

    func_dict={
            "install": install, 
            "run": run, 
            "start": start, 
            "stop": stop, 
            "monitor": monitor, 
            }
    sys.exit(func_dict[action]())
