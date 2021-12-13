#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, dch_src, dch_dst, dch_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, dch_src, dch_dst, None, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    dch_mem=dch_info_dict["db_info"].get("dch_mem")
    # 环境配置
    log.logger.debug("环境配置")
    sysctl_conf_file="/etc/sysctl.d/dch.conf"
    sysctl_conf_text="""\
            net.core.somaxconn=2048
            vm.overcommit_memory=1
    """
    dch_sh_text=f"""\
            export DCH_HOME={dch_dir}
            export PATH=$DCH_HOME/bin:$PATH
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
            "dch_sh":{
                "config_file": "/etc/profile.d/dch.sh", 
                "config_context": dch_sh_text, 
                "mode": "w"
                }
            }

    # dch配置, 根据主从配置dch文件
    log.logger.debug("配置dch")
    if dch_info_dict.get("cluster_info") is None:
        role="stand-alone"
    else:
        cluster_info_dict=dch_info_dict["cluster_info"]
        role=cluster_info_dict.get("role")
    log.logger.debug(f"{role=}")

    if role=="stand-alone" or role=="master":
        slaveof_master_port=""
    elif role=="slave":
        master_host=cluster_info_dict.get("master_host")
        master_port=cluster_info_dict.get("master_port")
        slaveof_master_port=f"replicaof {master_host} {master_port}"
    log.logger.debug(f"{slaveof_master_port=}")

    dch_io_threads=dch_info_dict["db_info"]["dch_io_threads"]
    dch_conf_text=f"""\
            # NETWORK
            bind 0.0.0.0
            protected-mode yes
            port {dch_port}
            tcp-backlog 511
            ## unixsocket /tmp/dch.sock
            ## unixsocketperm 700
            timeout 0
            tcp-keepalive 300
            
            # GENERAL
            daemonize yes
            supervised no
            pidfile {dch_dir}/dch.pid
            databases 16
            always-show-logo yes                             
            
            # log
            loglevel notice
            logfile "{dch_dir}/logs/dch.log"
            ## syslog-enabled no
            ## syslog-ident dch
            ## syslog-facility local0
            
            slowlog-log-slower-than 10000
            slowlog-max-len 128
            
            # SNAPSHOTTING
            dir {dch_dir}/data
            
            save 900 1
            save 300 10
            save 60 10000
            
            stop-writes-on-bgsave-error yes
            rdbcompression yes
            rdbchecksum yes
            dbfilename dump.rdb
            rdb-del-sync-files no                      
            
            # REPLICATION 
            # repl-timeout 60
            # master
            repl-diskless-sync no
            repl-diskless-sync-delay 5
            repl-disable-tcp-nodelay yes
            repl-backlog-size 1mb
            repl-backlog-ttl 3600
            
            # slave
            {slaveof_master_port}
            masterauth {dch_password}
            # masteruser <username>
            # repl-ping-replica-period 10
            repl-diskless-load disabled
            replica-serve-stale-data yes
            replica-read-only yes
            replica-priority 100
            # min-replicas-to-write 3
            # min-replicas-max-lag 10
            # replica-announce-ip 5.5.5.5
            # replica-announce-port 1234
            # replica-ignore-maxmemory yes

            
            # KEYS TRACKING
            # tracking-table-max-keys 1000000         
            
            # SECURITY 
            acllog-max-len 128
            # aclfile /dream/dch/conf/users.acl
            requirepass {dch_password}
            
            # CLIENTS 
            # maxclients 10000
            
            # MEMORY MANAGEMENT	
            maxmemory {dch_mem}
            # maxmemory-policy noeviction
            # maxmemory-samples 5
            # active-expire-effort 1
            
            # LAZY FREEING 
            lazyfree-lazy-eviction no
            lazyfree-lazy-expire no
            lazyfree-lazy-server-del no
            replica-lazy-flush no
            lazyfree-lazy-user-del no
            
            # THREADED I/O
            io-threads {dch_io_threads}
            io-threads-do-reads no 
            # server_cpulist 0-7:2	
            # bio_cpulist 1,3	
            # aof_rewrite_cpulist 8-11
            # bgsave_cpulist 1,10-11
            
            # KERNEL OOM CONTROL  
            oom-score-adj no		
            oom-score-adj-values 0 200 800
            
            # APPEND ONLY MODE
            appendonly no
            appendfilename "appendonly.aof"
            appendfsync everysec
            no-appendfsync-on-rewrite no
            auto-aof-rewrite-percentage 100
            auto-aof-rewrite-min-size 64mb
            aof-load-truncated yes
            aof-use-rdb-preamble yes                 
            
            # LUA SCRIPTING
            lua-time-limit 5000
            
            # DCH CLUSTER
            # cluster-enabled yes
            # cluster-config-file nodes-6379.conf
            # cluster-node-timeout 15000
            # cluster-replica-validity-factor 10
            # cluster-migration-barrier 1
            # cluster-require-full-coverage yes
            # cluster-replica-no-failover no
            # cluster-allow-reads-when-down no
            # cluster-announce-ip 10.1.1.5
            # cluster-announce-port 6379
            # cluster-announce-bus-port 6380
            
            # LATENCY MONITOR
            latency-monitor-threshold 0
            
            # EVENT NOTIFICATION
            notify-keyspace-events ""       
            # GOPHER SERVER
            # gopher-enabled no             
            
            # ADVANCED CONFIG 
            hash-max-ziplist-entries 512
            hash-max-ziplist-value 64
            list-max-ziplist-size -2
            list-compress-depth 0
            set-max-intset-entries 512
            zset-max-ziplist-entries 128
            zset-max-ziplist-value 64
            hll-sparse-max-bytes 3000
            stream-node-max-bytes 4096
            stream-node-max-entries 100
            activerehashing yes
            client-output-buffer-limit normal 0 0 0
            client-output-buffer-limit replica 256mb 64mb 60
            client-output-buffer-limit pubsub 32mb 8mb 60
            # client-query-buffer-limit 1gb
            # proto-max-bulk-len 512mb
            hz 10
            dynamic-hz yes
            aof-rewrite-incremental-fsync yes
            rdb-save-incremental-fsync yes
            # lfu-log-factor 10
            # lfu-decay-time 1
            
            # ACTIVE DEFRAGMENTATION
            # activedefrag no
            # active-defrag-ignore-bytes 100mb
            # active-defrag-threshold-lower 10
            # active-defrag-threshold-upper 100
            # active-defrag-cycle-min 1
            # active-defrag-cycle-max 25
            # active-defrag-max-scan-fields 1000
            jemalloc-bg-thread yes
            ignore-warnings ARM64-COW-BUG
            """
    config_dict.update(
            {
                "dch_conf": {
                    "config_file": f"{dch_dir}/conf/dch.conf",
                    "config_context": dch_conf_text,
                    "mode": "w"
                    }
                }
            )

    # Sentinel配置
    if sentinel_flag:
        log.logger.debug("配置sentinel")
        monitor_host=sentinel_info.get("monitor_host")
        monitor_port=sentinel_info.get("monitor_port")
        replicas_num=len(sentinel_info.get("replicas_members"))

        if replicas_num <= 2:
            quorum=1
        elif (replicas_num % 2)==0:
            quorum=replicas_num/2
        else:
            quorum=int(replicas_num/2)+1
        sentinel_conf_text=f"""\
                protected-mode no
                port {sentinel_port}
                daemonize yes
                dir "{dch_dir}/data"
                logfile "{dch_dir}/logs/sentinel.log"
                pidfile {dch_dir}/sentinel.pid

                {sentinel_password_str}
                #sentinel sentinel-user <username>
                #sentinel sentinel-pass <password>

                sentinel monitor mymaster {monitor_host} {monitor_port} {quorum}
                sentinel auth-pass mymaster {dch_password}
                sentinel deny-scripts-reconfig yes
                sentinel down-after-milliseconds mymaster 5000
                sentinel failover-timeout mymaster 180000

                sentinel resolve-hostnames yes
                sentinel announce-hostnames no
        """
        config_dict.update(
                {
                    "sentinel_conf": {
                        "config_file": f"{dch_dir}/conf/sentinel.conf",
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
    dch_start_command=f"cd {dch_dir} && bin/dch-server conf/dch.conf"
    log.logger.debug(f"dch启动: {dch_start_command=}")
    result, msg=common.exec_command(dch_start_command)
    if result:
        log.logger.debug(f"检测端口: {dch_port} ")
        if not common.port_exist([dch_port]):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        sentinel_start_command=f"cd {dch_dir} && bin/dch-sentinel conf/sentinel.conf"
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
    dch_stop_command=f"cd {dch_dir} && bin/dch-cli -a {dch_password} shutdown"
    log.logger.debug(f"dch停止: {dch_stop_command=}")
    result, msg=common.exec_command(dch_stop_command)
    if result:
        log.logger.debug(f"检测端口: {dch_port}")
        if not common.port_exist([dch_port], exist_or_not=False):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code

    if sentinel_flag:
        if sentinel_password_str == "":
            sentinel_stop_command=f"cd {dch_dir} && bin/dch-cli -p {sentinel_port} shutdown"
        else:
            sentinel_stop_command=f"cd {dch_dir} && bin/dch-cli -a {sentinel_password} -p {sentinel_port} shutdown"
        log.logger.debug(f"sentinel停止: {sentinel_stop_command=}")
        result, msg=common.exec_command(sentinel_stop_command)
        if result:
            log.logger.debug(f"检测端口: {sentinel_port}")
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
    log=common.Logger({"remote": log_remote_level}, loggger_name="dch")

    if dch_dst is None:
        dch_dir=f"{located}/{dch_src}"
    else:
        dch_dir=f"{located}/{dch_dst}"
    dch_info_dict=conf_dict[f"{softname}_info"]
    dch_port=dch_info_dict["db_info"]["dch_port"]
    dch_password=dch_info_dict["db_info"].get("dch_password")
    port_list=[dch_port]

    # 是否启用sentinel
    sentinel_info=dch_info_dict.get("sentinel_info")
    if  sentinel_info is None:
        sentinel_flag=0
    else:
        sentinel_flag=1
        sentinel_port=sentinel_info.get("sentinel_port")
        port_list.append(sentinel_port)
        sentinel_password=sentinel_info.get("sentinel_password")
        if sentinel_password is None or sentinel_password.strip()=="":
            sentinel_password_str=""
        else:
            sentinel_password_str=f"requirepass {sentinel_password}"

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
