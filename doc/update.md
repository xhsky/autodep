# 更新



## 代码更新
- 代码更新分为前端和后端两种方式



### 前端代码打包方式

- 说明
  - 将前端代码目录打包为`tar.gz`格式的压缩包
  - 该压缩包内只存在一个目录和一个文件。目录即代码目录, 其目录下是代码文件；文件即更新信息

- 压缩包组织格式示例
  ```
  - code.tar.gz
    - code
      - a.html
      - b.html
      - dir1
        c.html
    - update.json
    	{
      	"mode": "platform|console",        // platform为平台更新，"console"为离线手动更新
      	"id": "1111",				    // 项目id
      	"type": "code",				    // 代码更新
      	"update_info":{
      		"type": "frontend",			// 前端代码
      		"host": [host1,host2],		 	// 更新的主机
        		"dest": "/path/dir",			// 更新路径
        		"version": "11111",			  	// 代码版本
      	}
    	 }
  ```



### 后端代码打包方式

- 说明

  - 将后端`jar`包打包为`tar.gz`格式的压缩包
  - 该压缩包内只存在一个目录和一个文件。目录即代码目录, 其目录下是单一的`jar`包；文件即更新信息

- 压缩包组织格式示例

  ```
  - code.tar.gz
    - code
      - code.jar
    - code_update.json
    	{
    	"mode": "platform|console",        // platform为平台更新，"console"为离线手动更新
      	"id": "1111",				    // 项目id
      	"type": "code",				    // 代码更新
      	"update_info":{
      		"type": "backend",				// 后端代码
      		"host": [host1,host2],		 	// 更新的主机
        		"dest": "/path/dir",			// 更新路径
        		"version": "11111",			  	// 代码版本
      	}
    	 }
  ```
  
  
  

## 数据库更新

- 说明

  - 将`数据文件`目录打包为`tar.gz`格式的压缩包
  - 该压缩包内只存在一个目录和文件。 目录即代码目录, 其目录下是单一的`sql`文件；文件即更新信息

- 压缩包组织格式示例

	```
  - data.tar.gz
    - data
      - data.sql
    - update.json
      {
      	"mode": "platform|console",        // platform为平台更新，"console"为离线手动更新
      	"id": "1111",				    // 项目id
      	"type": "db",				    // 数据库更新
      	"update_info":{
      		"type": "mysql"					// 更新的数据库类型
      		"host": "hostname",				 // 更新的主机
        		"user": "username",				 // 数据库的用户
        		"password": "password",			  // 数据库的密码
	      		"db": "db_name"					// 数据库名称
    	}
      }
  ```
  
  

## 更新方式

```
# ./main.py -p/-t update file1.tar.gz file2.tar.gz
```



