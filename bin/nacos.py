#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os
from libs import common
from libs.env import log_remote_level, nacos_src, nacos_dst, nacos_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=0
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, nacos_src, nacos_dst, nacos_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code
    #else:
    #    nacos_dst=nacos_src

    jvm_mem=nacos_info_dict["jvm_mem"]
    jvm_command=f"sed 's/-Xms512m -Xmx512m -Xmn256m/-Xms{jvm_mem} -Xmx{jvm_mem}/' {nacos_dir}/bin/startup.sh"

    nacos_conf_text=f"""\
            # Spring Boot 
            server.servlet.contextPath=/nacos
            server.port={web_port}

            # Network 
            nacos.inetutils.prefer-hostname-over-ip=True
            # nacos.inetutils.ip-address=

            # Connection pool 
            db.pool.config.connectionTimeout=30000
            db.pool.config.validationTimeout=10000
            db.pool.config.maximumPoolSize=20
            db.pool.config.minimumIdle=2

            nacos.naming.empty-service.auto-clean=true
            nacos.naming.empty-service.clean.initial-delay-ms=50000
            nacos.naming.empty-service.clean.period-time-ms=30000

            # Metrics 
            management.metrics.export.elastic.enabled=false
            management.metrics.export.influx.enabled=false

            # Access Log 
            server.tomcat.accesslog.enabled=true
            server.tomcat.accesslog.pattern=%h %l %u %t "%r" %s %b %D %{{User-Agent}}i %{{Request-Source}}i
            server.tomcat.basedir=

            # Access Control
            #spring.security.enabled=false
            nacos.security.ignore.urls=/,/error,/**/*.css,/**/*.js,/**/*.html,/**/*.map,/**/*.svg,/**/*.png,/**/*.ico,/console-ui/public/**,/v1/auth/**,/v1/console/health/**,/actuator/**,/v1/console/server/**
            nacos.core.auth.system.type=nacos
            nacos.core.auth.enabled=false
            nacos.core.auth.default.token.expire.seconds=18000
            nacos.core.auth.default.token.secret.key=SecretKey012345678901234567890123456789012345678901234567890123456789
            nacos.core.auth.caching.enabled=true
            nacos.core.auth.server.identity.key=111
            nacos.core.auth.server.identity.value=222

            nacos.istio.mcp.server.enabled=false
            """
    mode=nacos_info_dict["data_source"]["mode"]
    if mode=="mysql":
        db_host=nacos_info_dict["data_source"]["mysql_info"]["db_host"]
        db_port=nacos_info_dict["data_source"]["mysql_info"]["db_port"]
        db_name=nacos_info_dict["data_source"]["mysql_info"]["db_name"]
        db_user=nacos_info_dict["data_source"]["mysql_info"]["db_user"]
        db_password=nacos_info_dict["data_source"]["mysql_info"]["db_password"]
        mysql_conf_text=f"""\
            # Config Module
            spring.datasource.platform=mysql
            db.num=1
            db.url.0=jdbc:mysql://{db_host}:{db_port}/{db_name}?characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true&useUnicode=true&useSSL=false&serverTimezone=UTC
            db.user.0={db_user}
            db.password.0={db_password}
        """
        nacos_conf_text=f"{nacos_conf_text}\n{mysql_conf_text}"
        jvm_command=f"sed 's/-server -Xms{jvm_mem} -Xmx{jvm_mem} -Xmn1g/-server -Xms1g -Xmx1g -Xmn256m/' {nacos_dir}/bin/startup.sh"
    nacos_conf_file=f"{nacos_dir}/conf/application.properties"
    config_dict={
            "nacos_conf":{
                "config_file": nacos_conf_file, 
                "config_context": nacos_conf_text, 
                "mode": "w"
                }
            }

    if cluster_flag:
        cluster_info_text="\n".join(cluster_info_dict["members"])
        cluster_conf_file=f"{nacos_dir}/conf/cluster.conf"
        config_dict["cluster_conf"]={
                "config_file": cluster_conf_file, 
                "config_context": cluster_info_text, 
                "mode": "w"
                }
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
    result, msg=common.config(config_dict)
    if result:
        log.logger.debug("修改jvm")
        result, msg=common.exec_command(jvm_command)
        if result:
            return_value=normal_code
        else:
            log.logger.error(msg)
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    if cluster_flag:
        if nacos_info_dict["data_source"]["mode"]=="mysql":
            start_command=f"cd {nacos_dir} ; ./bin/startup.sh"
        else:
            start_command=f"cd {nacos_dir} ; ./bin/startup.sh -p embedded"
    else:
        start_command=f"bash -lc 'cd {nacos_dir} ; ./bin/startup.sh -m standalone'"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command, timeout=180)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def start():
    """启动
    """
    return run()

def stop():
    """关闭
    """
    return_value=normal_code
    stop_command=f"bash -lc 'cd {nacos_dir} ; ./bin/shutdown.sh'"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    # softname = "nacos"
    # action = "start"
    # conf_json = '{"ip": "127.0.0.1", "software": ["set_hosts", "jdk", "nacos"], "located": "/dream/", "nacos_info": {"web_port": 8848, "jvm_mem": "1G", "data_source": {"mode": "derby"}}, "hosts_info": {"hostname": "web1", "hosts": ["127.0.0.1 web1"]}, "pkg_file": "/opt/python3/pkgs/nacos-server-1.4.2-9050.tar.gz"}'
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, loggger_name="nacos")

    located=conf_dict["located"]
    nacos_dir=f"{located}/{nacos_src}"
    nacos_info_dict=conf_dict["nacos_info"]
    web_port=nacos_info_dict["web_port"]
    port_list=[web_port]
    cluster_flag=False
    cluster_info_dict=nacos_info_dict.get("cluster_info")
    if cluster_info_dict is not None:
        cluster_flag=True
        raft_port=cluster_info_dict["raft_port"]
        port_list.append(raft_port)

    if action=="install":
        sys.exit(install())
    elif action=="run":
        sys.exit(run())
    elif action=="start":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(activated_code)
        elif status_value==stopped_code:
            sys.exit(start())
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action=="stop":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(stop())
        elif status_value==stopped_code:
            sys.exit(stopped_code)
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action=="monitor":
        sys.exit(monitor())
    else:
        sys.exit(error_code)

