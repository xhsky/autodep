#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs.common import Logger

def main():
    """
        将libXau, libxcb, SDL2安装包放入编译好的ffmpeg下的deps目录
    """
    #action, weight, soft_file, conf_json=sys.argv[1:5]
    #action, args_json=sys.argv[1:]
    a=sys.argv[2]
    print(a)
    exit()
    #args_dict=json.loads(args_json)
    softname=conf_dict["softname"]
    conf_dict=args_dict["config_args"]

    log=Logger({"remote", "debug"})

    # 安装
    if action=="install":
        located=conf_dict.get("located")
        value, msg=common.install(soft_file, "ffmpeg", "ffmpeg", "deps", located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")

    elif action=="start":
            log.logger.info(f"{soft_name}无须启动")

if __name__ == "__main__":
    main()
