#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, jdk_src, jdk_dst, jdk_pkg_dir, jdk_version

def main():
    action, conf_json=sys.argv[1:]
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

if __name__ == "__main__":
    main()
