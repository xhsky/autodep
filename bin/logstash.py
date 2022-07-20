#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2022年 07月 14日
# duan

import sys, json
from libs import common, tools
from libs.env import log_remote_level, logstash_src, logstash_dst, logstash_pkg_dir, \
    normal_code, error_code, activated_code, stopped_code, abnormal_code


def install():
    """安装
    """
    return_value = normal_code
    pkg_file = conf_dict["pkg_file"]
    value, msg = common.install(pkg_file, logstash_src, logstash_dst, logstash_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # 配置

    logstash_conf_context = tools.render("../config/templates/logstash/logstash.conf.tem", conf_dict=conf_dict)
    logstash_yml_context = tools.render("../config/templates/logstash/logstash.yml.tem", conf_dict=conf_dict)
    jvm_options_context = tools.render("../config/templates/logstash/jvm.options.tem", conf_dict=conf_dict)
    start_sh_context = tools.render("../config/templates/logstash/start.sh.tem")
    stop_sh_context = tools.render("../config/templates/logstash/stop.sh.tem")

    config_dict = {
        "logstash_conf": {
            "config_file": f"{logstash_dir}/config/logstash.conf",
            "config_context": logstash_conf_context,
            "mode": "w"
        },
        "logstash_yml": {
            "config_file": f"{logstash_dir}/config/logstash.yml",
            "config_context": logstash_yml_context,
            "mode": "w"
        },
        "jvm_options": {
            "config_file": f"{logstash_dir}/config/jvm.options",
            "config_context": jvm_options_context,
            "mode": "w"
        },
        "start_sh": {
            "config_file": f"{logstash_dir}/start.sh",
            "config_context": start_sh_context,
            "mode": "w"
        },
        "stop_sh": {
            "config_file": f"{logstash_dir}/stop.sh",
            "config_context": stop_sh_context,
            "mode": "w"
        },
    }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg = common.config(config_dict)
    if result:
        log.logger.debug("添加logstash相关配置文件")
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def run():
    """运行
    """
    return_value = normal_code
    command = f"cd {logstash_dir} && /bin/bash ./start.sh"
    log.logger.debug(f"{command=}")

    result, msg = common.exec_command(command, timeout=60)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return_value = error_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def start():
    """启动
    """
    return run()


def stop():
    """停止
    """
    return_value = normal_code
    command = f"cd {logstash_dir} && /bin/bash ./stop.sh"
    log.logger.debug(f"{command=}")

    result, msg = common.exec_command(command)
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
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)


if __name__ == "__main__":
    # softname, action, conf_json = sys.argv[1:]
    softname = "elasticsearch"
    action = "stop"
    conf_json = '''
    {
    "ip": "127.0.0.1",
    "pkg_file": "/opt/python3/pkgs/logstash-7.17.5-linux-x86_64.tar.gz",
    "software": ["logstash"],
    "located": "/dream/",
    "logstash_info": {
        "api_http_port": 9600,
        "pipeline_workers": 4,
        "jvm_mem": "2G",
        "confs": {
            "index_nc": {
                "input": {
                    "jdbc": {
                        "jdbc_connection_string": "jdbc:mysql://192.168.0.178:3306/dsfa_ky?characterEncoding=UTF-8&useSSL=false&autoReconnect=true&serverTimezone=UTC",
                        "jdbc_user": "duan",
                        "jdbc_password": "duanxinyi",
                        "jdbc_driver_library": "/duan/softwares/logstash/jdbcDriver/mysql-connector-java-8.0.19.jar",
                        "jdbc_driver_class": "com.mysql.jdbc.Driver",
                        "jdbc_default_timezone": "Asia/Shanghai",
                        "jdbc_paging_enabled": "true",
                        "jdbc_page_size": "1000",
                        "statement_filepath": "/duan/softwares/logstash/config/dsfa_ky.sql",
                        "schedule": "*/2 * * * *",
                        "use_column_value": "false",
                        "tracking_column": "update_date"
                    }
                },
                "output": {
                    "elasticsearch": {
                        "hosts": "192.168.0.178:9200",
                        "index": "dsfa_syslog_operate_%{+YYYY-MM-dd}",
                        "user": "elastic",
                        "password": "DreamSoft_123"
                    },
                    "stdout": {
                        "codec": "json_lines"
                    }
                }
            },
            "web_log": {
                "input": {
                    "tcp": {"port": 9400}
                },
                "filter": {
                    "kv": {"field_split_pattern": "&{3}"}
                },
                "output": {
                    "elasticsearch": {
                        "hosts": "192.168.0.178:9200",
                        "index": "dsfa_syslog_operate_%{+YYYY-MM-dd}",
                        "user": "elastic",
                        "password": "DreamSoft_123"
                    }
                }
            }
        }
    }
}
    '''

    conf_dict = json.loads(conf_json)
    log = common.Logger({"remote": log_remote_level}, loggger_name="logstash")

    located = conf_dict.get("located")
    logstash_dir = f"{located}/{logstash_dst}"

    port_list = [conf_dict["logstash_info"]["api_http_port"], ]

    if action == "install":
        sys.exit(install())
    elif action == "run":
        sys.exit(run())
    elif action == "start":
        status_value = monitor()
        if status_value == activated_code:
            sys.exit(activated_code)
        elif status_value == stopped_code:
            sys.exit(start())
        elif status_value == abnormal_code:
            if stop() == normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action == "stop":
        status_value = monitor()
        if status_value == activated_code:
            sys.exit(stop())
        elif status_value == stopped_code:
            sys.exit(stopped_code)
        elif status_value == abnormal_code:
            if stop() == normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action == "monitor":
        sys.exit(monitor())
    else:
        sys.exit(error_code)
