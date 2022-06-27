# 自动化部署
用于自动化部署集群

## 说明
1. 本项目基于Centos7系统, x86架构测试, 用于自动安装, 配置, 优化常用软件
2. 本站点提供的形如`autodep-version-x64.tar.gz`文件为安装包
3. 本文所有操作均使用root用户
4. 需要每台主机的`root`用户且主机之间的`sshd`端口(默认22)相互连通

## 功能
1. 当前支持软件: nginx, jdk, tomcat, ffmpeg, redis, glusterfs, mysql
2. 当前支持集群: web集群(nginx+tomcat), redis主从-哨兵集群, glusterfs镜像集群, MySQL主从集群
3. 支持自动安装, 自动配置, 自动优化

## 配置文件
### 说明
1. 配置文件均为json格式
2. 在`autodep-1.0/autodep/config/`目录下有`init.json`和`arch.json`的示例文件, 可自行修改
3. 在`autodep-1.0/autodep/config/sample_config/`目录下有每个软件的示例文件, 可用来参考配置`arch.json`

### init.json文件

​	初始化配置文件, 格式为json, 用于指定主机信息

#### 格式
```
{
  "local_name": "web",                  // "local_name"用于指定运行安装程序的主机
  "web":{                               // "web"为下方"ip"所对应的主机域名, 在该集群中唯一, 可自定义
    "ip":"192.168.1.203",               // "ip"为主机ip
    "root_password":"111111",           // "root_password"为该主机对应的root密码
    "port":22                           // "port"为连接该主机的ssh端口
    }, 
  "hostname1":{                         // 将集群中每一台主机均按该格式写入
    ...
  }, 
  "hostname2":{
    ...
  }, 
  ...
}
```

### arch.json文件

​	安装信息文件, 格式为json, 用于指定部署的集群架构信息

#### 格式
```
{
  "web":{                                                    // 在init.json中定义的主机名称, 有且唯一. 
    "software": ["nginx", "jdk", "tomcat"],                  // "software"为要在该主机上安装的软件列表, 格式为[]
    "located": "/data/",                                     // "located"为软件安装目录
    "nginx_info":{                                           // "nginx_info"为nginx软件的属性信息, 一些软件需要有额外对应的属性信息以便于更好的安装. 具体信息请看软件属性
      "proxy_hosts": ["web1", "web2"]
     }, 
     ...
  }, 
  "web1":{                                                    // 在init.json中定义的主机名称
    "software": ["jdk", "tomcat"],                            // "software"为要在该主机上安装的软件列表, 格式为[]
    "located": "/data/",                                      // "located"为软件安装目录
  }, 
  ...
}
```

### 软件属性

#### nginx属性格式

```
{  
   "web":{
     "software": ["nginx"], 
     "located": "/data/", 
     "nginx_info":{                                            // nginx属性
       "proxy_hosts": ["web1", "web2"]                         // "proxy_hosts"指定负载的后端服务器名称
    }
}
```

#### jdk属性格式
```
{
  "web1":{
    "software": ["jdk"], 
    "located": "/data/"
  }
}
```

#### tomcat属性格式

```
{
  "web1":{
    "software": ["jdk", "tomcat"], 
    "located": "/data/"
  }
}
```

#### ffmpeg属性格式

```
{
  "web1":{
    "software": ["jdk", "tomcat", "ffmpeg"], 
    "located": "/data/"
  }
}
```

#### redis属性格式

##### redis单机属性格式

```
{
  "redis":{
    "software": ["redis"], 
    "located": "/data",
    "redis_info":{                                      // redis属性名称          
       "db_info":{                                      // redis数据库信息
         "redis_password": "b840fc02d5240454"           // 指定redis密码
       } 
    }
  }
}
```
##### redis主从+哨兵属性格式

```
{
  "redis1":{
    "software": ["redis"], 
    "located": "/data", 
    "redis_info":{                                      // redis属性名称
       "db_info":{
         "redis_password": "b840fc02d5240454"           // 主从密码需相同
       }, 
       "cluster_info":{                                 // redis集群信息
         "role": "master",                              // 当前redis1主机角色
         "master_host": "redis1"                        // 指定主从集群中的master主机名
       }
    }
  }, 
  "redis2":{
    "software": ["redis"], 
    "located": "/data", 
    "redis_info":{
       "db_info":{
         "redis_password": "b840fc02d5240454"           // 主从密码需相同
       }, 
       "cluster_info":{                                 // redis集群信息
         "role": "slave",                               // 当前redis1主机角色
         "master_host": "redis1"                        // 指定主从集群中的master主机名
       }
    }
  } 
}
```
#### glusterfs属性格式

##### glusterfs服务器+客户端属性格式

```
{
  "data1":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "server_info":{                             // glusterfs服务端属性
          "volume_dir": "/data_db",                 // 指定组成共享存储的服务端目录
          "members":["data1", "data2"]              // 指定组成共享存储的主机名称
        }, 
        "client_info":{                             // glusterfs客户端属性
          "mounted_host": "data1",                  // 指定要挂载共享存储的主机
          "mounted_dir": "/data_mount"              // 指定挂载该共享存储的主机目录
        }
    }
  }, 
  "data2":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "server_info":{                             // glusterfs服务端属性
          "volume_dir": "/data_db",                 // 指定组成共享存储的服务端目录
          "members":["data1", "data2"]              // 指定组成共享存储的主机名称
        }, 
        "client_info":{                             // glusterfs客户端属性
          "mounted_host": "data2",                  // 指定要挂载共享存储的主机
          "mounted_dir": "/data_mount"              // 指定挂载该共享存储的主机目录
        }
    }
  } 
}
```
##### glusterfs服务器属性格式

```
{
  "data1":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "server_info":{                             // glusterfs服务端属性
          "volume_dir": "/data_db",                 // 指定组成共享存储的服务端目录
          "members":["data1", "data2"]              // 指定组成共享存储的主机名称
        }
    }
  }, 
  "data2":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "server_info":{                             // glusterfs服务端属性
          "volume_dir": "/data_db",                 // 指定组成共享存储的服务端目录
          "members":["data1", "data2"]              // 指定组成共享存储的主机名称
        }
    }
  }
}
```
##### glusterfs客户端属性格式

```
{
  "web1":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "client_info":{                             // glusterfs客户端属性
          "mounted_host": "web1",                   // 指定要挂载共享存储的主机
          "mounted_dir": "/data_mount"              // 指定挂载该共享存储的主机目录
        }
    }
  }, 
  "web2":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{                              // glusterfs属性名称
        "client_info":{                             // glusterfs客户端属性
          "mounted_host": "web2",                   // 指定要挂载共享存储的主机
          "mounted_dir": "/data_mount"              // 指定挂载该共享存储的主机目录
        }
    }
  } 
}
```

#### mysql属性格式

##### mysql单机属性格式
```
{
  "mydb":{
    "software": ["mysql"], 
    "located": "/data/", 
    "mysql_info":{                                                 // mysql属性信息
        "db_info":{                                                // mysql数据库属性信息
          "root_password": "DreamSoft_135",                        // 指定MySQL的root密码, 需符合密码复杂度策略(至少8位, 包含数字, 字母大小写和特殊符号)
          "server_id": 1,                                          // 指定MySQL的编号, 不能和其它主机的MySQL编号相同
          "business_db": ["db1", "db2"],                           // 业务数据库名称, 会自动建立
          "business_user": ["user1", "user2"],                     // 每个业务数据库对应的用户
          "business_password": ["Dreamdb_111", "Dreamdb_222"]      // 每个业务用户对应的密码(需符合密码复杂度)
        }
    }
  }
}
```

##### mysql主从属性格式

```
{
  "mydb1":{
    "software": ["mysql"], 
    "located": "/data/", 
    "mysql_info":{                                                 // mysql属性信息
        "db_info":{                                                // mysql数据库属性信息
          "root_password": "DreamSoft_135",                        // 指定MySQL的root密码, 需符合密码复杂度策略(至少8位, 包含数字, 字母大小写和特殊符号)
          "server_id": 1,                                          // 指定MySQL的编号, 不能和其它主机的MySQL编号相同
          "business_db": ["db1", "db2"],                           // 业务数据库名称, 会自动建立
          "business_user": ["user1", "user2"],                     // 每个业务数据库对应的用户
          "business_password": ["Dreamdb_111", "Dreamdb_222"]      // 每个业务用户对应的密码(需符合密码复杂度)
        }, 
        "cluster_info":{                                           // MySQL集群信息
          "role": "master"                                         // MySQL集群中的角色
        }
    }
  }, 
  "mydb2":{
    "software": ["mysql"], 
    "located": "/data/", 
    "mysql_info":{                                                 // mysql属性信息
        "db_info":{                                                // mysql数据库属性信息
          "root_password": "DreamSoft_135",                        // 指定MySQL的root密码, 需符合密码复杂度策略(至少8位, 包含数字, 字母大小写和特殊符号)
          "server_id": 2,                                          // 指定MySQL的编号, 不能和其它主机的MySQL编号相同
          "business_db": ["db3", "db4"],                           // 业务数据库名称, 会自动建立. 此处不能写同步数据库
          "business_user": ["user3", "user4"],                     // 每个业务数据库对应的用户
          "business_password": ["Dreamdb_333", "Dreamdb_444"]      // 每个业务用户对应的密码(需符合密码复杂度)
        }, 
        "cluster_info":{                                           // MySQL集群信息
          "role": "slave"                                          // MySQL集群中的角色
          "sync_host": "mydb1",                                    // 当"role"为"slave"时, 要指定需同步的数据库主机
          "sync_dbs": ["db1", "db2"]                               // 同时指定需要同步的数据库(在mydb1中指定的业务数据库)
        }
    }
  } 
}
```

## 部署安装
*以9台服务器为例, 使用nginx+ 2 web + 2 redis(主从哨兵) + 2 mysql(主从) + 2 glusterfs*

1. 将安装包上传至某台服务器上
2. 解压
```
# tar -xf autodep-1.0-x84.tar.gz
# cd autodep/autodep
```
3. 编辑初始化配置文件, 指定集群中各个主机
```
# vim config/init.json
{
  "local_name": "web",
  "web":{
    "ip":"192.168.1.203", 
    "root_password":"111111", 
    "port":22
  },
  "web1":{
    "ip":"192.168.1.107", 
    "root_password":"111111", 
    "port":22
  },
  "web2":{
    "ip":"192.168.1.204", 
    "root_password":"111111", 
    "port":22
  },
  "redis1":{
    "ip":"192.168.1.206", 
    "root_password":"111111", 
    "port":22
  },
  "redis2":{
    "ip":"192.168.1.207", 
    "root_password":"111111", 
    "port":22
  },
  "data1":{
    "ip":"192.168.1.210", 
    "root_password":"111111", 
    "port":22
  },
  "data2":{
    "ip":"192.168.1.102", 
    "root_password":"111111", 
    "port":22
  },
  "db1":{
    "ip":"192.168.1.214", 
    "root_password":"111111", 
    "port":22
  },
  "db2":{
    "ip":"192.168.1.209", 
    "root_password":"111111", 
    "port":22
  }
}
```
4. 编辑架构配置文件, 指定集群架构
```
# vim config/arch.json
{
  "web":{
    "software": ["nginx"], 
    "located": "/data/", 
    "nginx_info":{
      "proxy_hosts": ["web1", "web2"]
     }
  },
  "data1":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{
        "server_info":{
          "volume_dir": "/data_db", 
          "members":["data1", "data2"]
        } 
    }
  }, 
  "data2":{
    "software": ["glusterfs"], 
    "located": "/data", 
    "glusterfs_info":{
        "server_info":{
          "volume_dir": "/data_db", 
          "members":["data1", "data2"]
        }
    }
  },
  "web1":{
    "software": ["jdk", "tomcat", "ffmpeg", "glusterfs"], 
    "located": "/data/", 
    "glusterfs_info":{
        "client_info":{
          "mounted_host": "data1", 
          "mounted_dir": "/data_mount"
        }
    }
  }, 
  "web2":{
    "software": ["jdk", "tomcat", "ffmpeg", "glusterfs"], 
    "located": "/data/", 
    "glusterfs_info":{
        "client_info":{
          "mounted_host": "data1", 
          "mounted_dir": "/data_mount"
        }
    }
  },
  "redis1":{
    "software": ["redis"], 
    "located": "/data", 
		"redis_info":{
       "db_info":{
         "redis_password": "b840fc02d524045429941cc15f59e41cb7be6c599"
       }, 
       "cluster_info":{
         "role": "master", 
         "master_host": "redis1"
       }
    }
  }, 
  "redis2":{
    "software": ["redis"], 
    "located": "/data", 
		"redis_info":{
       "db_info":{
         "redis_password": "b840fc02d524045429941cc15f59e41cb7be6c599"
       }, 
       "cluster_info":{
         "role": "slave", 
         "master_host": "redis1"
       }
    }
  },  
  "db1":{
    "software": ["mysql"], 
    "located": "/data/", 
    "mysql_info":{
        "db_info":{
          "root_password": "DreamSoft_135", 
          "server_id": 1, 
          "business_db": ["db1", "db2"], 
          "business_user": ["user1", "user2"], 
          "business_password": ["Dreamdb_111", "Dreamdb_222"]
        }
    }
  }, 
  "db2":{
    "software": ["mysql"], 
    "located": "/data/", 
    "mysql_info":{
        "db_info":{
          "root_password": "DreamSoft_246", 
          "server_id": 2, 
          "business_db": ["db3", "db4"], 
          "business_user": ["user3", "user4"], 
          "business_password": ["Dreamdb_333", "Dreamdb_444"]
        }, 
        "cluster_info":{
          "role": "slave" ,
          "sync_host": "db1",
          "sync_dbs": ["db1", "db2"] 
        }
    }
  }
}
```

5. 初始化
```
# ./init.py
检测配置文件中账号端口等信息, 请等待...                                                                                                                                       
主机初始化..                                                                                                                                                                  
本机生成密钥对                                                                                                                                                                
                                                                                                                                                                              
主机web环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为web完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机web1环境初始化...                                                                                                                                                         
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为web1完成                                                                                                                                                          
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 

主机web2环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为web2完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机redis1环境初始化...                                                                                                                                                       
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为redis1完成                                                                                                                                                        
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 

主机redis2环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为redis2完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机data1环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为data1完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机data2环境初始化...                                                                                                                                                        
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为data2完成                                                                                                                                                         
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机db1环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为db1完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机db2环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为db2完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
初始化完成             

各主机信息如下:                                                                                                                                                               
主机名: web                                                                                                                                                                   
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64                                                                                                                                    
CPU核心数:      8(0.5%)                                                                                                                                                       
内存大小:       9.61G(5.9%)                                                                                                                                                   
磁盘(/):        896.29G(0.7%)                                                                                                                                                 
磁盘(/boot):    1014.00M(16.8%)                                                                                                                                               
                                                                                                                                                                              
主机名: web1                                                                                                                                                                  
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64                                                                                                                                    
CPU核心数:      8(0.0%)                                                                                                                                                       
内存大小:       9.61G(4.7%)                                                                                                                                                   
磁盘(/):        896.29G(0.2%)                                                                                                                                                 
磁盘(/boot):    1014.00M(16.8%)                                                                                                                                               
                                                                                                                                                                              
主机名: web2                                                                                                                                                                  
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.8%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: redis1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: redis2                                                                                                                                                                
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.6%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: data1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: data2
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.6%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: db1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: db2
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

```

5. 开始部署
```
# ./main.py
[root@node autodep]# ./main.py                                                                                                                                                
开始集群部署...                                                                                                                                                               
                                                                                                                                                                              
web部署...                                                                                                                                                                    
                                                                                                                                                                              
安装并配置nginx...                                                                                                                                                            
nginx安装完成                                                                                                                                                                 
nginx配置优化完成                                                                                                                                                             

data1部署...

启动并配置glusterfs...
GlusterFS共享存储创建成功

data2部署...

启动并配置glusterfs...
Error: 
                                                                                                                                                                              
web1部署...                                                                                                                                                                   
                                                                                                                                                                              
安装并配置jdk...                                                                                                                                                              
jdk安装完成                                                                                                                                                                   
jdk配置完成                                                                                                                                                                   
                                                                                                                                                                              
安装并配置tomcat...                                                                                                                                                           
Tomcat安装完成                                                                                                                                                                
Tomcat配置环境变量完成                                                                                                                                                        
Tomcat配置优化完成                                                                                                                                                            
                                                                                                                                                                              
安装并配置ffmpeg...                                                                                                                                                           
ffmpeg安装完成                                                                                                                                                                

安装并配置glusterfs...
glusterfs挂载成功
                                                                                                                                                                              
web2部署...                                                                                                                                                                   
                                                                                                                                                                              
安装并配置jdk...                                                                                                                                                              
jdk安装完成                                                                                                                                                                   
jdk配置完成           

安装并配置tomcat...
Tomcat安装完成
Tomcat配置环境变量完成
Tomcat配置优化完成

安装并配置ffmpeg...
ffmpeg安装完成

安装并配置glusterfs...
glusterfs挂载成功

redis1部署...

安装并配置redis...
Redis安装完成
Redis配置环境变量完成
Sentinel安装配置完成
Redis(master)配置优化完成

redis2部署...

安装并配置redis...
Redis安装完成
Redis配置环境变量完成
Sentinel安装配置完成
Redis(slave)配置优化完成

data1部署...
安装并配置glusterfs...
GlusterFS安装完成

data2部署...

安装并配置glusterfs...
GlusterFS安装完成

db1部署...

安装并配置mysql...
MySQL安装完成
MySQL配置完成

db2部署...

安装并配置mysql...
MySQL安装完成
MySQL配置完成

开始集群启动...

web部署...

启动并配置nginx...
nginx启动完成

web1部署...
启动并配置jdk...                                                                                                                                                              
jdk无须启动

启动并配置tomcat...
Tomcat启动完成

启动并配置ffmpeg...
ffmpeg无须启动

web2部署...
                                                                                                
启动并配置jdk...
jdk无须启动                                                                                     
            
启动并配置tomcat...                                                                             
Tomcat启动完成
                                                                                                
启动并配置ffmpeg...
ffmpeg无须启动

redis1部署...                                                                                             

启动并配置redis...
Redis(master)启动成功
Sentinel启动成功

redis2部署...

启动并配置redis...
Redis(slave)启动成功
Sentinel启动成功


db1部署...

启动并配置mysql...
MySQL初始化中...
MySQL更改初始密码完成
MySQL用户配置完成
MySQL(master)配置完成

db2部署...

启动并配置mysql...
MySQL初始化中...
MySQL更改初始密码完成
MySQL用户配置完成
MySQL(slave)配置完成
```

