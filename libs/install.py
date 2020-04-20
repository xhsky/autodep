#!/usr/bin/env python
# coding:utf8
# sky

from libs import client

class soft(object):
    def  __init__(self):
        self.obj=client.Client()

    def tar_install(self, soft_name, ip, port, install_dir):
        remote_file=f"/tmp/{soft_name.split('/')[-1]}"
        self.obj.scp(ip, port, "root", soft_name, remote_file)
        command=f"tar -xf {remote_file} -C {install_dir} && echo 0"
        status=self.obj.exec(ip, port, command)
        return status

    def pkg_install(self):
        pass

    def control(self, action):
        install_dir=self.__res["base_dir"]
        user=self.__res["run_user"]
        sw=soft.install(user, self.__soft_name, install_dir)
        # 获取已安装软件信息
        key=common.host_ip()
        soft_info=self.__db_client.hget(define.host_soft_info_key, key)
        soft_info_dict=json.loads(soft_info)

        pid=soft_info_dict[self.__soft_name]
        if action=="start":
            if self.__soft_name in soft_info_dict and pid=="0":
                sw.set_env()
                pid=sw.start()
                if pid!=0:
                    soft_info_dict[self.__soft_name]=pid
                    soft_info=json.dumps(soft_info_dict)
                    self.__db_client.hset(define.host_soft_info_key, key, soft_info)
                else:
                    self.__log.log("error", "无法启动, 请查看%s状态" % self.__soft_name)
            else:
                self.__log.log("error", "%s 是启动状态" % self.__soft_name)
                
        elif action=="stop":
            if self.__soft_name in soft_info_dict and pid!="0":
                res=sw.stop(pid)
                if res==0:
                    soft_info_dict[self.__soft_name]="0"
                    soft_info=json.dumps(soft_info_dict)
                    self.__db_client.hset(define.host_soft_info_key, key, soft_info)
            else:
                self.__log.log("error", "%s 未启动" % self.__soft_name)
                
        else:
            self.__log.log("error", "action: %s" % action)

def soft_install():
    log=logger.logger()
    db_client=db.get_redis_conn()
    ip=common.host_ip()


    log.log("info", "安装程序开始准备接收安装信息...")
    subs=db_client.subscribe(define.soft_install_info_key)
    for i in subs.listen():
        if i["type"]=="message":
            args=json.loads(i["data"])
            if args["ip"]==ip:
                # 安装
                if args["type"]=="install":
                    for soft_name in args["soft_name"]:
                        local_soft_obj=local_soft(soft_name)
                        local_soft_obj.local_install()
                # 控制
                elif args["type"]=="control":
                    local_soft_obj=local_soft(args["soft_name"])
                    local_soft_obj.local_control(args["action"])
                # 其它
                else:
                    pass


if __name__ == "__main__":
    pass


