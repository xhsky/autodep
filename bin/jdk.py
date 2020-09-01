#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    soft_name="jdk"

    log=common.Logger(None, "info", "remote")

    # 安装
    if action=="install":
        value, msg=common.install(soft_file, "jdk", "jdk", None, located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"Error: 解压安装包失败: {msg}")
            return 

        # 配置
        jdk_sh_context=f"""\
                export JAVA_HOME={located}/jdk
                export PATH=$JAVA_HOME/bin:$PATH
        """
        config_dict={
                "jdk_sh":{
                    "config_file": "/etc/profile.d/jdk.sh", 
                    "config_context": jdk_sh_context
                    }
                }
        result, msg=common.config(config_dict)
        if result==1:
            log.logger.info(f"{soft_name}配置完成")
        else:
            log.logger.error(f"{soft_name}配置出错: {msg}")

    if action=="start":
        log.logger.info(f"{soft_name}无须启动")

if __name__ == "__main__":
    main()
