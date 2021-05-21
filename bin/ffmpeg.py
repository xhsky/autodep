#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
#from libs.common import Logger, install
from libs import common
from libs.env import log_remote_level, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

'''
def main():
    """
        将libXau, libxcb, SDL2安装包放入编译好的ffmpeg下的deps目录
    """
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)

    log=Logger({"remote": log_remote_level})

    flag=0
    # 安装
    if action=="install":
        located=conf_dict["located"]
        pkg_file=conf_dict["pkg_file"]
        value, msg=install(pkg_file, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, located)
        if not value:
            flag=1
            log.logger.error(msg)
        sys.exit(flag)

    elif action=="run" or action=="start" or action=="stop":
        sys.exit(flag)
'''

def install():
    """安装
    将libXau, libxcb, SDL2安装包放入编译好的ffmpeg下的deps目录
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
