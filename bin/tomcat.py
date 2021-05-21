#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import shutil
from libs import common
from libs.env import log_remote_level, tomcat_src, tomcat_dst, tomcat_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    log=common.Logger({"remote": log_remote_level}, loggger_name="tomcat")
    tomcat_dir=f"{located}/{tomcat_dst}"
    tomcat_info_dict=conf_dict["tomcat_info"]
    http_port=tomcat_info_dict["port"].get("http_port")
    shutdown_port=tomcat_info_dict["port"].get("shutdown_port")
    #ajp_port=tomcat_info_dict["port"].get("ajp_port")
    ajp_port=8009
    port_list=[
            http_port, 
            shutdown_port
            ]

    flag=0
    # 安装
    if action=="install":
        pkg_file=conf_dict["pkg_file"]
        value, msg=common.install(pkg_file, tomcat_src, tomcat_dst, tomcat_pkg_dir, located)
        if not value:
            log.logger.error(msg)
            flag=1
            sys.exit(flag)

        # 配置
        try:
            # 删除tomcat原有程序目录
            log.logger.debug("删除默认程序")
            webapps_dir=f"{tomcat_dir}/webapps"
            for i in os.listdir(webapps_dir):
                shutil.rmtree(f"{webapps_dir}/{i}")
        except Exception as e:
            log.logger.error(str(e))

        jvm_mem=tomcat_info_dict.get("jvm_mem")
        min_threads, max_threads=tomcat_info_dict.get("threads")
        max_connections=tomcat_info_dict.get("max_connections")

        tomcat_sh_context=f"""\
            export CATALINA_HOME={tomcat_dir}
            export PATH=$CATALINA_HOME/bin:$PATH
        """
        server_xml_context=f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!--
              Licensed to the Apache Software Foundation (ASF) under one or more
              contributor license agreements.  See the NOTICE file distributed with
              this work for additional information regarding copyright ownership.
              The ASF licenses this file to You under the Apache License, Version 2.0
              (the "License"); you may not use this file except in compliance with
              the License.  You may obtain a copy of the License at

                  http://www.apache.org/licenses/LICENSE-2.0

              Unless required by applicable law or agreed to in writing, software
              distributed under the License is distributed on an "AS IS" BASIS,
              WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
              See the License for the specific language governing permissions and
              limitations under the License.
            -->
            <!-- Note:  A "Server" is not itself a "Container", so you may not
                 define subcomponents such as "Valves" at this level.
                 Documentation at /docs/config/server.html
             -->
            <Server port="{shutdown_port}" shutdown="SHUTDOWN">
              <Listener className="org.apache.catalina.startup.VersionLoggerListener" />
              <!-- Security listener. Documentation at /docs/config/listeners.html
              <Listener className="org.apache.catalina.security.SecurityListener" />
              -->
              <!--APR library loader. Documentation at /docs/apr.html -->
              <Listener className="org.apache.catalina.core.AprLifecycleListener" SSLEngine="on" />
              <!-- Prevent memory leaks due to use of particular java/javax APIs-->
              <Listener className="org.apache.catalina.core.JreMemoryLeakPreventionListener" />
              <Listener className="org.apache.catalina.mbeans.GlobalResourcesLifecycleListener" />
              <Listener className="org.apache.catalina.core.ThreadLocalLeakPreventionListener" />

              <!-- Global JNDI resources
                   Documentation at /docs/jndi-resources-howto.html
              -->
              <GlobalNamingResources>
                <!-- Editable user database that can also be used by
                     UserDatabaseRealm to authenticate users
                -->
                <Resource name="UserDatabase" auth="Container"
                          type="org.apache.catalina.UserDatabase"
                          description="User database that can be updated and saved"
                          factory="org.apache.catalina.users.MemoryUserDatabaseFactory"
                          pathname="conf/tomcat-users.xml" />
              </GlobalNamingResources>

              <!-- A "Service" is a collection of one or more "Connectors" that share
                   a single "Container" Note:  A "Service" is not itself a "Container",
                   so you may not define subcomponents such as "Valves" at this level.
                   Documentation at /docs/config/service.html
               -->
              <Service name="Catalina">

                <!--The connectors can use a shared executor, you can define one or more named thread pools-->
                <!--
                <Executor name="tomcatThreadPool" namePrefix="catalina-exec-"
                    maxThreads="150" minSpareThreads="4"/>
                -->


                <!-- A "Connector" represents an endpoint by which requests are received
                     and responses are returned. Documentation at :
                     Java HTTP Connector: /docs/config/http.html
                     Java AJP  Connector: /docs/config/ajp.html
                     APR (HTTP/AJP) Connector: /docs/apr.html
                     Define a non-SSL/TLS HTTP/1.1 Connector on port 8080
                -->
                <Connector port="{http_port}" protocol="HTTP/1.1"
                           maxHttpHeaderSize="8192"  
                           maxThreads="{max_threads}"  
                           minSpareThreads="{min_threads}"  
                           enableLookups="false"  
                           compression="on"  
                           compressionMinSize="2048"  
                           URIEncoding="utf-8"  
                           acceptCount="300"  
                           disableUploadTimeout="true"
                           maxConnections="{max_connections}"
                           connectionTimeout="20000"
                           redirectPort="8443" />
                <!-- A "Connector" using the shared thread pool-->
                <!--
                <Connector executor="tomcatThreadPool"
                           port="8080" protocol="HTTP/1.1"
                           connectionTimeout="20000"
                           redirectPort="8443" />
                -->
                <!-- Define an SSL/TLS HTTP/1.1 Connector on port 8443
                     This connector uses the NIO implementation. The default
                     SSLImplementation will depend on the presence of the APR/native
                     library and the useOpenSSL attribute of the
                     AprLifecycleListener.
                     Either JSSE or OpenSSL style configuration may be used regardless of
                     the SSLImplementation selected. JSSE style configuration is used below.
                -->
                <!--
                <Connector port="8443" protocol="org.apache.coyote.http11.Http11NioProtocol"
                           maxThreads="150" SSLEnabled="true">
                    <SSLHostConfig>
                        <Certificate certificateKeystoreFile="conf/localhost-rsa.jks"
                                     type="RSA" />
                    </SSLHostConfig>
                </Connector>
                -->
                <!-- Define an SSL/TLS HTTP/1.1 Connector on port 8443 with HTTP/2
                     This connector uses the APR/native implementation which always uses
                     OpenSSL for TLS.
                     Either JSSE or OpenSSL style configuration may be used. OpenSSL style
                     configuration is used below.
                -->
                <!--
                <Connector port="8443" protocol="org.apache.coyote.http11.Http11AprProtocol"
                           maxThreads="150" SSLEnabled="true" >
                    <UpgradeProtocol className="org.apache.coyote.http2.Http2Protocol" />
                    <SSLHostConfig>
                        <Certificate certificateKeyFile="conf/localhost-rsa-key.pem"
                                     certificateFile="conf/localhost-rsa-cert.pem"
                                     certificateChainFile="conf/localhost-rsa-chain.pem"
                                     type="RSA" />
                    </SSLHostConfig>
                </Connector>
                -->

                <!-- Define an AJP 1.3 Connector on port 8009 -->
                <!--
                <Connector protocol="AJP/1.3"
                           address="::1"
                           port="{ajp_port}"
                           redirectPort="8443" />
                -->

                <!-- An Engine represents the entry point (within Catalina) that processes
                     every request.  The Engine implementation for Tomcat stand alone
                     analyzes the HTTP headers included with the request, and passes them
                     on to the appropriate Host (virtual host).
                     Documentation at /docs/config/engine.html -->

                <!-- You should set jvmRoute to support load-balancing via AJP ie :
                <Engine name="Catalina" defaultHost="localhost" jvmRoute="jvm1">
                -->
                <Engine name="Catalina" defaultHost="localhost">

                  <!--For clustering, please take a look at documentation at:
                      /docs/cluster-howto.html  (simple how to)
                      /docs/config/cluster.html (reference documentation) -->
                  <!--
                  <Cluster className="org.apache.catalina.ha.tcp.SimpleTcpCluster"/>
                  -->

                  <!-- Use the LockOutRealm to prevent attempts to guess user passwords
                       via a brute-force attack -->
                  <Realm className="org.apache.catalina.realm.LockOutRealm">
                    <!-- This Realm uses the UserDatabase configured in the global JNDI
                         resources under the key "UserDatabase".  Any edits
                         that are performed against this UserDatabase are immediately
                         available for use by the Realm.  -->
                    <Realm className="org.apache.catalina.realm.UserDatabaseRealm"
                           resourceName="UserDatabase"/>
                  </Realm>

                  <Host name="localhost"  appBase="webapps"
                        unpackWARs="true" autoDeploy="true">

                    <!-- SingleSignOn valve, share authentication between web applications
                         Documentation at: /docs/config/valve.html -->
                    <!--
                    <Valve className="org.apache.catalina.authenticator.SingleSignOn" />
                    -->

                    <!-- Access log processes all example.
                         Documentation at: /docs/config/valve.html
                         Note: The pattern used is equivalent to using pattern="common" -->
                    <Valve className="org.apache.catalina.valves.AccessLogValve" directory="logs"
                           prefix="localhost_access_log" suffix=".txt"
                           pattern="%h %l %u %t &quot;%r&quot; %s %b" />

                  </Host>
                </Engine>
              </Service>
            </Server>
            """
        setevn_sh_context=f"""\
            #!/bin/bash
            # sky 

            JAVA_OPTS="-server -XX:+AggressiveOpts -XX:+UseBiasedLocking -XX:+DisableExplicitGC -XX:+UseConcMarkSweepGC -XX:+UseParNewGC -XX:+CMSParallelRemarkEnabled -XX:+UseFastAccessorMethods -XX:+UseCMSInitiatingOccupancyOnly -Djava.security.egd=file:/dev/./urandom -Djava.awt.headless=true"

            JAVA_OPTS="$JAVA_OPTS -Xms{jvm_mem} -Xmx{jvm_mem} -Xss512k -XX:LargePageSizeInBytes=128M -XX:MaxTenuringThreshold=11 -XX:MetaspaceSize=200m -XX:MaxMetaspaceSize=256m -XX:MaxNewSize=256m"

            UMASK=0022

            CATALINA_PID=$CATALINA_HOME/bin/catalina.pid
            """
        config_dict={
                "server_xml": {
                    "config_file": f"{tomcat_dir}/conf/server.xml", 
                    "config_context": server_xml_context, 
                    "mode": "w"
                    }, 
                "setenv_sh":{
                    "config_file": f"{tomcat_dir}/bin/setenv.sh", 
                    "config_context": setevn_sh_context, 
                    "mode": "w"
                    }, 
                "tomcat_sh":{
                    "config_file": f"/etc/profile.d/tomcat.sh", 
                    "config_context": tomcat_sh_context, 
                    "mode": "w"
                }
            }

        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
        result, msg=common.config(config_dict)
        if result:
            command=f"{tomcat_dir}/bin/catalina.sh configtest"
            log.logger.debug(f"配置文件检测: {command=}")
            status, result=common.exec_command(command)
            # 返回值32512为apr未安装报错, 忽略
            if status:
                if result.returncode != 0 and result.returncode != 32512:
                    log.logger.error(result.stderr)
                    flag=1
            else:
                log.logger.error(msg)
                flag=1
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)

    elif action=="run":
        command=f"set -m ; {tomcat_dir}/bin/catalina.sh start" 
        log.logger.debug(f"{command=}")
        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
                flag=1
            else:
                log.logger.debug(f"检测端口: {port_list=}")
                if not common.port_exist(port_list):
                    flag=2
        else:
            log.logger.error(result)
            flag=1

        sys.exit(flag)
    elif action=="start":
        pass
    elif action=="stop":
        pass

def install():
    """安装
    """
    pass

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    log=common.Logger({"remote": log_remote_level}, loggger_name="tomcat")
    tomcat_dir=f"{located}/{tomcat_dst}"
    tomcat_info_dict=conf_dict["tomcat_info"]
    http_port=tomcat_info_dict["port"].get("http_port")
    shutdown_port=tomcat_info_dict["port"].get("shutdown_port")
    #ajp_port=tomcat_info_dict["port"].get("ajp_port")
    ajp_port=8009
    port_list=[
            http_port, 
            shutdown_port
            ]

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
