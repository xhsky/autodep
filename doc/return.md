# 平台接口格式



## 初始化格式

```
{
	"project_id": str,
	"mode": "init",
	"result": True,
	"stats": {
		"ip1":{
			"stats_value": True|False,
			"stats_message": ""
		},
		"ip2":{
		
		}
	},
	host_info": {
		"ip1":{
			"os_name": "CentOS Linux release 7.5.1804 (Core)",
			"kernel_version": "3.10.0-862.el7.x86_64",
			"disk": {
				"/path1": ["总大小", N],
				"/path2": ["总大小", N]
			}
			"CPU":[str, N],
			"Mem": [str, N],
			"Port": [
				"port1":[pid, name_str],
				...
			]
		},
		"ip2":{
		
		}
	}
}
```



## 安装格式

```
{
	"project_id": str,
	"mode": "install",
	"result": True,
	"stats": {
		"node1": {
			"soft1": True|False,
			"soft2": True|False
		}
		"node2": {
		
		}
	
	}
}
```



## 启动格式

```
{
	"project_id": str,
	"mode": "start",
	"result": True,
	"stats": {
		"node1": {
			"soft1": True|False,
			"soft2": True|False
		}
		"node2": {
		
		}
	
	}
}
```



## 更新格式

```
{
	"project_id": str,
	"mode": "update",
	"result": True|False
	"stats":{
		"pkg1":{
			"host1": True|False,
			"host2": True|False
		},
		"pkg2":{
			...
		}
	}
}
```

