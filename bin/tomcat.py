import sys, os, json
import shutil
from libs import common, tools
from libs.env import log_remote_level, tomcat_src, tomcat_dst, tomcat_pkg_dir, \
    normal_code, error_code, activated_code, stopped_code, abnormal_code


def install():
    """安装
    """
    return_value = normal_code
    pkg_file = conf_dict["pkg_file"]
    value, msg = common.install(pkg_file, tomcat_src, tomcat_dst, None, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    log.logger.debug("环境配置")
    tomcat_info_dict = conf_dict["tomcat_info"]
    ajp_port = 8009
    jvm_mem = tomcat_info_dict.get("jvm_mem")
    min_threads, max_threads = tomcat_info_dict.get("threads")
    max_connections = tomcat_info_dict.get("max_connections")
    server_xml_context = tools.render("config/templates/tomcat/server.xml.tem", shutdown_port=shutdown_port,
                                      http_port=http_port, \
                                      min_threads=min_threads, max_threads=max_threads, \
                                      ajp_port=ajp_port, max_connections=max_connections)
    tomcat_sh_context = tools.render("config/templates/tomcat/tomcat.sh.tem", tomcat_dir=tomcat_dir)
    setenv_sh_context = tools.render("config/templates/tomcat/setenv.sh.tem", jvm_mem=jvm_mem, located=located)

    config_dict = {
        "server_xml": {
            "config_file": f"{tomcat_dir}/conf/server.xml",
            "config_context": server_xml_context,
            "mode": "w"
        },
        "setenv_sh": {
            "config_file": f"{tomcat_dir}/bin/setenv.sh",
            "config_context": setenv_sh_context,
            "mode": "w"
        },
        "tomcat_sh": {
            "config_file": f"/etc/profile.d/tomcat.sh",
            "config_context": tomcat_sh_context,
            "mode": "w"
        }
    }

    log.logger.debug("配置server.xml")
    result, msg = common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def run():
    return_value = normal_code
    start_command = f"{located}/{tomcat_dst}/bin/startup.sh"
    log.logger.debug(f"{start_command=}")
    result, msg = common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return_value = error_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def start():
    return run()


def stop():
    return_value = normal_code
    start_command = f"{located}/{tomcat_dst}/bin/shutdown.sh"
    result, msg = common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return_value = error_code
    else:
        log.logger.error(msg)
        return_value = error_code
    return return_value


def monitor():
    return common.soft_monitor("localhost", port_list)


if __name__ == "__main__":
    softname, action, conf_json = sys.argv[1:]
    # softname = "tomcat"
    # action = "run"
    # conf_json = '{"ip": "127.0.0.1","software": ["tomcat"], "located": "/dream/", "tomcat_info":{"jvm_mem": "1G","threads":[400, 1500],"max_connections": 10000,"port":{"http_port": 8080,"shutdown_port": 8005, "ajp_port": 8009}},"pkg_file": "/opt/python3/pkgs/apache-tomcat-8.5.51.tar.gz"}'
    conf_dict = json.loads(conf_json)
    located = conf_dict.get("located")

    log = common.Logger({"remote": log_remote_level}, loggger_name="tomcat")
    tomcat_dir = f"{located}/{tomcat_dst}"
    tomcat_info_dict = conf_dict["tomcat_info"]
    http_port = tomcat_info_dict["port"].get("http_port")
    shutdown_port = tomcat_info_dict["port"].get("shutdown_port")
    ajp_port = tomcat_info_dict["port"].get("ajp_port")
    # ajp_port=8009

    port_list = [
        http_port,
        shutdown_port
    ]

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
