#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import psutil
import shutil
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    soft_name="Tomcat"
    log=common.Logger(None, "info", "remote")
    dst="tomcat"

    # 安装
    if action=="install":
        value, msg=common.install(soft_file, "apache-tomcat-", dst, None, located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.info(f"{soft_name}安装失败: {msg}")
            return 

        # 配置
        try:
            # 删除tomcat原有程序目录
            webapps_dir=f"{located}/{dst}/webapps"
            for i in os.listdir(webapps_dir):
                shutil.rmtree(f"{webapps_dir}/{i}")
        except Exception as e:
            log.logger.error(f"{soft_name}删除原有项目出错: {e}")

        mem=psutil.virtual_memory()
        jvm_mem=int(mem[0] * float(weight) /1024/1024)
        tomcat_sh_context=f"""\
            export CATALINA_HOME={located}/{dst}
            export PATH=$CATALINA_HOME/bin:$PATH
        """
        server_xml_context="""\
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
            <Server port="8005" shutdown="SHUTDOWN">
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
                <Connector port="8080" protocol="HTTP/1.1"
                           maxHttpHeaderSize="8192"  
                           maxThreads="1500"  
                           minSpareThreads="400"  
                           enableLookups="false"  
                           compression="on"  
                           compressionMinSize="2048"  
                           URIEncoding="utf-8"  
                           acceptCount="600"  
                           disableUploadTimeout="true"
                           maxConnections="10000"
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
                           port="8009"
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

            JAVA_OPTS="$JAVA_OPTS -Xms{jvm_mem}M -Xmx{jvm_mem}M -Xss512k -XX:LargePageSizeInBytes=128M -XX:MaxTenuringThreshold=11 -XX:MetaspaceSize=200m -XX:MaxMetaspaceSize=256m -XX:MaxNewSize=256m"

            UMASK=0022

            CATALINA_PID=$CATALINA_HOME/bin/catalina.pid
            """
        config_dict={
                "server_xml": {
                    "config_file": f"{located}/{dst}/conf/server.xml", 
                    "config_context": server_xml_context, 
                    "mode": "w"
                    }, 
                "setenv_sh":{
                    "config_file": f"{located}/{dst}/bin/setenv.sh", 
                    "config_context": setevn_sh_context, 
                    "mode": "w"
                    }, 
                "tomcat_sh":{
                    "config_file": f"/etc/profile.d/tomcat.sh", 
                    "config_context": tomcat_sh_context, 
                    "mode": "w"
                }
            }

        result, msg=common.config(config_dict)
        if result==1:
            command=f"{located}/{dst}/bin/catalina.sh configtest &> /dev/null"
            value=os.system(command)
            # 返回值32512为apr未安装报错, 忽略
            if value==0 or value==32512:
                log.logger.info(f"{soft_name}配置优化完成")
            else:
                log.logger.error(f"{soft_name}配置优化失败:{value}")
        else:
            log.logger.error(f"{soft_name}配置写入失败:{msg}")

    elif action=="start":
        command=f"set -m ; {located}/{dst}/bin/catalina.sh start &> /dev/null" 
        result=os.system(command)
        if result==0:
            if common.port_exist(8080, 300):
                log.logger.info(f"{soft_name}启动完成")
            else:
                log.logger.error(f"{soft_name}启动超时")
        else:
            log.logger.error(f"Error: {soft_name}启动失败")

if __name__ == "__main__":
    main()
