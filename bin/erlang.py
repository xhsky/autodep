#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, erl_src, erl_dst, erl_pkg_dir, erl_version

def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)

    log=common.Logger({"remote": log_remote_level})

    flag=0
    # 安装
    if action=="install":
        located=conf_dict.get("located")
        pkg_file=conf_dict["pkg_file"]
        erl_dest=f"{located}/{erl_dst}"
        value, msg=common.install(pkg_file, erl_src, erl_dest, erl_pkg_dir, located)
        if not value:
            flag=1
            log.logger.error(msg)
            sys.exit(flag)

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
            flag=1
        sys.exit(flag)
    elif action=="run" or action=="start" or action=="stop":
        sys.exit(flag)

if __name__ == "__main__":
    main()
