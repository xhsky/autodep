#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common
from libs.env import log_remote_level, python_src, python_dst, python_pkg_dir, \
    normal_code, error_code, activated_code, stopped_code, abnormal_code


def install():
    """安装
    """
    create_dir_command = f"mkdir -p {jupyter_path}"
    log.logger.debug(f"{create_dir_command=}")
    result, msg = common.exec_command(create_dir_command)
    if result:
        return_value = normal_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def run():
    """运行
    """
    return_value = normal_code
    token = conf_dict["jupyter_info"]["token"]
    jupyter_server_config_py_text = f'''
c.ServerApp.allow_remote_access = True
c.ServerApp.shutdown_no_activity_timeout = 0
c.ServerApp.port = {port}
c.ServerApp.ip = '*'
c.ServerApp.disable_check_xsrf = True
c.ServerApp.token = {token}
    '''
    jupyter_server_sh_text = f'''
#!/bin/bash


action=$1
python_path={located}/python3.10.1
jupyter_path={jupyter_path}
config_file=${{jupyter_path}}/jupyter_server_config.py
log_file=${{jupyter_path}}/jupyter_server.log
pid_file=${{jupyter_path}}/jupyter_server.pid




function start() {{
    if [ -f "${{pid_file}}" ];then
        pid=`cat ${{pid_file}}`
        PID=`ps ax | grep ${{pid}} | grep jupyter | grep -v grep | awk '{{print $1}}'`
        if [ $PID ]; then
            echo "jupyter server进程已存在。"
            echo "Pid: ${{pid}}"
            exit 0
        fi
    fi
    export LD_LIBRARY_PATH={{python_path}}/lib:$LD_LIBRARY_PATH
    nohup ${{python_path}}/bin/jupyter server --config=${{config_file}} --allow-root > ${{log_file}} 2>&1 & echo $! > ${{pid_file}}
    pid=`cat ${{pid_file}}`
    PID=`ps ax | grep ${{pid}} | grep jupyter | grep -v grep | awk '{{print $1}}'`
    if [ $PID ]; then
        echo "jupyter server已启动成功。"
        echo "Pid: ${{pid}}"
    else 
        echo "未启动成功。请检查配置是否正确。"
    fi
    exit 0

}}


function stop() {{
    if [ -f "${{pid_file}}" ];then
        pid=`cat ${{pid_file}}`
        kill $pid > /dev/null
        rm -f ${{pid_file}}
        echo "程序已关闭"
        return 0
    else
        echo "程序未启动"
        return 0
    fi
}}


if [ -z "$1" ]; then
  echo "Usage: $0 start|restart|stop"
  exit 127
elif [ "$action" == "start" ]; then
  start
elif [ "$action" == "stop" ]; then
  stop
  exit $?
elif [ "$action" == "restart" ]; then
  stop
  start
elif [ "$action" == "check" ]; then
  start
else
  echo "Usage: $0 start|stop|restart|check"
fi
'''
    config_dict = {
        "jupyter_conf": {
            "config_file": f"{jupyter_path}/jupyter_server_config.py",
            "config_context": jupyter_server_config_py_text,
            "mode": "w"
        },
        "jupyter_sh": {
            "config_file": f"{jupyter_path}/jupyter_server.sh",
            "config_context": jupyter_server_sh_text,
            "mode": "w"
        }
    }

    jupyter_enabled_text = start_command
    config_dict.update(
        {
            "dch_sentinel_enabled": {
                "config_file": "/etc/rc.local",
                "config_context": jupyter_enabled_text,
                "mode": "r+"
            }
        }
    )

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg = common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return_value = error_code

    return_value = start()
    return return_value


def start():
    """启动
    """
    return_value = normal_code
    log.logger.debug(f"{start_command=}")
    result, msg = common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, seconds=1200):
            return_value = error_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def stop():
    """关闭
    """
    return_value = normal_code
    stop_command = f"bash {jupyter_path}/jupyter_server.sh stop"
    log.logger.debug(f"{stop_command=}")
    result, msg = common.exec_command(stop_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return_value = error_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def monitor():
    """监控
    """
    return activated_code


if __name__ == "__main__":
    softname, action, conf_json = sys.argv[1:]
    conf_dict = json.loads(conf_json)
    located = conf_dict["located"]
    jupyter_path = f"{located}/jupyter_server"
    port = conf_dict["jupyter_info"]["port"]
    port_list = [port,]
    log = common.Logger({"remote": log_remote_level}, loggger_name="python")
    start_command = f"bash {jupyter_path}/jupyter_server.sh start"

    func_dict = {
        "install": install,
        "run": run,
        "start": start,
        "stop": stop,
        "monitor": monitor,
    }
    sys.exit(func_dict[action]())
