#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, redis_src, redis_dst, redis_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, redis_src, redis_dst, None, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    redis_mem=redis_info_dict["db_info"].get("redis_mem")
    # 环境配置
    log.logger.debug("环境配置")
    sysctl_conf_file="/etc/sysctl.d/redis.conf"
    sysctl_conf_text="""\
            net.core.somaxconn=2048
            vm.overcommit_memory=1
    """
    redis_sh_text=f"""\
            export REDIS_HOME={redis_dir}
            export PATH=$REDIS_HOME/bin:$PATH
    """
    hugepage_disabled=f"echo never > /sys/kernel/mm/transparent_hugepage/enabled\n"
    config_dict={
            "sysctl_conf":{
                "config_file": sysctl_conf_file, 
                "config_context": sysctl_conf_text, 
                "mode": "w"
                }, 
            "rc_local":{
                "config_file": "/etc/rc.local", 
                "config_context": hugepage_disabled, 
                "mode": "r+"
                }, 
            "redis_sh":{
                "config_file": "/etc/profile.d/redis.sh", 
                "config_context": redis_sh_text, 
                "mode": "w"
                }
            }

    # redis配置, 根据主从配置redis文件
    log.logger.debug("配置redis")
    if redis_info_dict.get("cluster_info") is None:
        role="stand-alone"
    else:
        cluster_info_dict=redis_info_dict["cluster_info"]
        role=cluster_info_dict.get("role")
    log.logger.debug(f"{role=}")

    if role=="stand-alone" or role=="master":
        slaveof_master_port=""
    elif role=="slave":
        master_host=cluster_info_dict.get("master_host")
        master_port=cluster_info_dict.get("master_port")
        slaveof_master_port=f"slaveof {master_host} {master_port}"
    log.logger.debug(f"{slaveof_master_port=}")

    redis_conf_text=f"""\
            protected-mode no
            port {redis_port}
            tcp-backlog 511
            timeout 0
            tcp-keepalive 300
            daemonize yes
            supervised no
            pidfile "{redis_dir}/redis.pid"
            loglevel notice
            logfile "{redis_dir}/logs/redis.log"
            # syslog-enabled no
            # syslog-ident redis
            # syslog-facility local0
            databases 16
            always-show-logo yes

            save 900 1
            save 300 10
            save 60 10000

            stop-writes-on-bgsave-error no
            rdbcompression yes
            rdbchecksum yes

            dbfilename "dump.rdb"
            dir "{redis_dir}/data"

            {slaveof_master_port}

            masterauth "{password}"
            requirepass "{password}"
            replica-serve-stale-data yes

            replica-read-only yes

            repl-diskless-sync no

            repl-diskless-sync-delay 5
            # repl-ping-slave-period 10
            # repl-timeout 60
            repl-disable-tcp-nodelay no
            # repl-backlog-size 1mb
            # repl-backlog-ttl 3600
            replica-priority 100

            # maxclients 10000
            maxmemory {redis_mem}
            # maxmemory-policy noeviction

            lazyfree-lazy-eviction no
            lazyfree-lazy-expire no
            lazyfree-lazy-server-del no
            replica-lazy-flush no

            appendonly no
            appendfilename "appendonly.aof"
            appendfsync everysec
            # appendfsync no
            no-appendfsync-on-rewrite no
            auto-aof-rewrite-percentage 100
            auto-aof-rewrite-min-size 64mb
            aof-load-truncated yes
            aof-use-rdb-preamble no

            lua-time-limit 5000

            # cluster-enabled yes
            # cluster-config-file nodes-6379.conf
            # cluster-node-timeout 15000
            # cluster-slave-validity-factor 10
            # cluster-migration-barrier 1
            # cluster-require-full-coverage yes

            slowlog-max-len 128
            latency-monitor-threshold 0

            hash-max-ziplist-entries 512
            hash-max-ziplist-value 64

            list-max-ziplist-size -2
            list-compress-depth 0
            set-max-intset-entries 512
            zset-max-ziplist-entries 128
            zset-max-ziplist-value 64

            hll-sparse-max-bytes 3000
            activerehashing yes
            client-output-buffer-limit normal 0 0 0
            client-output-buffer-limit replica 256mb 64mb 60
            client-output-buffer-limit pubsub 32mb 8mb 60
            hz 10
            aof-rewrite-incremental-fsync yes
            """
    config_dict.update(
            {
                "redis_conf": {
                    "config_file": f"{redis_dir}/conf/redis.conf",
                    "config_context": redis_conf_text,
                    "mode": "w"
                    }
                }
            )

    # Sentinel配置
    if sentinel_flag:
        log.logger.debug("配置sentinel")
        #sentinel_port=sentinel_info.get("sentinel_port")
        monitor_host=sentinel_info.get("monitor_host")
        monitor_port=sentinel_info.get("monitor_port")

        sentinel_conf_text=f"""\
                protected-mode no
                port {sentinel_port}
                daemonize yes
                dir "{redis_dir}/data"
                logfile "{redis_dir}/logs/sentinel.log"
                sentinel monitor mymaster {monitor_host} {monitor_port} 1
                sentinel auth-pass mymaster {password}
                sentinel deny-scripts-reconfig yes
                sentinel down-after-milliseconds mymaster 5000
        """
        config_dict.update(
                {
                    "sentinel_conf": {
                        "config_file": f"{redis_dir}/conf/sentinel.conf",
                        "config_context": sentinel_conf_text,
                        "mode": "w"
                        }
                    }
                )

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        command=f"sysctl -p {sysctl_conf_file} && echo never > /sys/kernel/mm/transparent_hugepage/enabled"
        log.logger.debug(f"刷新配置: {command=}")
        result=common.exec_command(command)
        if not result:
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
    # exec使用get_pty, redis配置为后台运行, 但未启动完全时, 断开依然会停止, 故使用sleep 2让其完全启动
    redis_start_command=f"cd {redis_dir} && bin/redis-server conf/redis.conf"
    log.logger.debug(f"redis启动: {redis_start_command=}")
    result, msg=common.exec_command(redis_start_command)
    if result:
        log.logger.debug(f"检测端口: {redis_port} ")
        if not common.port_exist([redis_port]):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        #sentinel_port=sentinel_info.get("sentinel_port")
        sentinel_start_command=f"cd {redis_dir} && bin/redis-sentinel conf/sentinel.conf"
        log.logger.debug(f"sentinel启动: {sentinel_start_command=}")
        result, msg=common.exec_command(sentinel_start_command)
        if result:
            log.logger.debug(f"检测端口: {sentinel_port} ")
            if not common.port_exist([sentinel_port]):
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
    """停止
    """
    return_value=normal_code
    redis_stop_command=f"cd {redis_dir} && bin/redis-cli -a {password} shutdown"
    log.logger.debug(f"redis停止: {redis_stop_command=}")
    result, msg=common.exec_command(redis_stop_command)
    if result:
        log.logger.debug(f"检测端口: {redis_port} ")
        if not common.port_exist([redis_port], exist_or_not=False):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        sentinel_stop_command=f"cd {redis_dir} && bin/redis-cli -a {password} -p {sentinel_port} shutdown"
        log.logger.debug(f"sentinel停止: {sentinel_stop_command=}")
        result, msg=common.exec_command(sentinel_stop_command)
        if result:
            log.logger.debug(f"检测端口: {sentinel_port} ")
            if not common.port_exist([sentinel_port], exist_or_not=False):
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
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    log=common.Logger({"remote": log_remote_level}, loggger_name="redis")

    redis_dir=f"{located}/{redis_dst}"
    redis_info_dict=conf_dict[f"{softname}_info"]
    redis_port=redis_info_dict["db_info"]["redis_port"]
    password=redis_info_dict["db_info"].get("redis_password")
    port_list=[redis_port]

    # 是否启用sentinel
    sentinel_info=redis_info_dict.get("sentinel_info")
    if  sentinel_info is None:
        sentinel_flag=0
    else:
        sentinel_flag=1
        sentinel_port=sentinel_info.get("sentinel_port")
        port_list.append(sentinel_port)

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
