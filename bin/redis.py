#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import psutil
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    soft_name="Redis"
    sentinel_soft_name="Sentinel"
    log=common.Logger(None, "info", "remote")
    dst="redis"
    redis_port=6379
    sentinel_port=26379
    role="stand-alone"

    located=conf_dict.get("located")
    if action=="install":
        # 安装
        value, msg=common.install(soft_file,"redis-", dst, None, located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.info(f"{soft_name}安装失败: {msg}")
            return 

        # 配置
        sysctl_conf_file="/etc/sysctl.d/redis.conf"
        sysctl_conf_text="""\
                net.core.somaxconn=1024
                vm.overcommit_memory=1
        """
        redis_sh_text=f"""\
                export REDIS_HOME={located}/dst
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
        result, msg=common.config(config_dict)

        if result == 1:
            log.logger.info(f"{soft_name}配置环境变量完成")
            result=os.system(f"sysctl -p {sysctl_conf_file} &> /dev/null && echo never > /sys/kernel/mm/transparent_hugepage/enabled")
            if result == 0:
                log.logger.info(f"{soft_name}环境变量生效")
            else:
                log.logger.error(f"{soft_name}环境变量未生效: {result}")
        else:
            log.logger.error(f"{soft_name}配置环境变量失败: {msg}")

        password=conf_dict.get("redis_info").get("db_info").get("redis_password")
        mem=psutil.virtual_memory()
        mem=int(mem[0] * float(weight) /1024/1024)

        # 配置sentinel文件
        # 若存在集群设置, 则配置sentinel
        cluster_info_dict=conf_dict.get("redis_info").get("cluster_info")
        if cluster_info_dict is not None:
            role=cluster_info_dict.get("role")
            master_host=cluster_info_dict.get("master_host")
            sentinel_conf_text=f"""\
                    protected-mode no
                    port {sentinel_port}
                    daemonize yes
                    dir "{located}/{dst}/data"
                    logfile "{located}/{dst}/logs/sentinel.log"
                    sentinel monitor mymaster {master_host} {redis_port} 1
                    sentinel auth-pass mymaster {password}
                    sentinel deny-scripts-reconfig yes
                    sentinel down-after-milliseconds mymaster 5000
            """
            config_dict={
                    "sentinel_conf": {
                        "config_file": f"{located}/{dst}/conf/sentinel.conf", 
                        "config_context": sentinel_conf_text, 
                        "mode": "w"
                        }
                    }
            result, msg=common.config(config_dict)
            if result==1:
                log.logger.info(f"{sentinel_soft_name}配置完成")
            else:
                log.logger.error(f"{sentinel_soft_name}配置失败: {msg}")
        else:
            #role="master"
            master_host=""

        # 根据主从配置redis文件
        if role=="stand-alone" or role=="master":
            slaveof_master_port=""
        elif role=="slave":
            slaveof_master_port=f"slaveof {master_host} {redis_port}"
        redis_conf_text=f"""\
                protected-mode no
                port {redis_port}
                tcp-backlog 511
                timeout 0
                tcp-keepalive 300
                daemonize yes
                supervised no
                pidfile "{located}/{dst}/redis.pid"
                loglevel notice
                logfile "{located}/{dst}/logs/redis.log"
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
                dir "{located}/{dst}/data"

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
                maxmemory {mem}M
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
        config_dict={
                "redis_conf": {
                    "config_file": f"{located}/{dst}/conf/redis.conf", 
                    "config_context": redis_conf_text, 
                    "mode": "w"
                    }
                }
        result, msg=common.config(config_dict)
        if result==1:
            log.logger.info(f"{soft_name}({role})配置优化完成")
        else:
            log.logger.error(f"{soft_name}({role})配置优化失败: {msg}")

    elif action=="start":
        cluster_flag=0
        cluster_info_dict=conf_dict.get("redis_info").get("cluster_info")
        if cluster_info_dict is not None:
            cluster_flag=1
            role=cluster_info_dict.get("role")

        ## exec使用get_pty, redis配置为后台运行, 但未启动完全时, 断开依然会停止, 故使用sleep 2让其完全启动
        redis_start_command=f"cd {located}/{dst} && bin/redis-server conf/redis.conf"
        result=os.system(redis_start_command)
        if result==0:
            if common.port_exist(redis_port):
                log.logger.info(f"{soft_name}({role})启动成功")
            else:
                log.logger.error(f"{soft_name}({role})启动超时")
        else:
            log.logger.error(f"{soft_name}({role})启动失败")

        if cluster_flag:
            sentinel_start_command=f"cd {located}/{dst} && bin/redis-sentinel conf/sentinel.conf"
            result=os.system(sentinel_start_command)
            if result==0:
                if common.port_exist(sentinel_port):
                    log.logger.info(f"{sentinel_soft_name}启动成功")
                else:
                    log.logger.error(f"{sentinel_soft_name}启动超时")
            else:
                log.logger.error(f"{sentinel_soft_name}启动失败")

if __name__ == "__main__":
    main()
