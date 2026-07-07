# b_client_xray 极简实现计划

## 1. 项目定位

`b_client_xray` 是一个给个人自用的 B 端 Xray 管理面板。

它只解决一个问题：

```text
A 端 x-ui 通过 VLESS/VMess over mKCP 连接到 B 端
B 端 Xray 接收连接
B 端 Xray 使用 freedom outbound 按 A 端携带的目标地址转发流量
```

第一版不做复杂平台，不做多用户系统，不做节点订阅，不做流量统计，不做多服务器同步。

## 2. 最小目标

第一版只需要实现这些能力：

```text
1. 配置 B 端 Xray 目录
2. 管理一个或多个 mKCP 入站
3. 生成 B 端 Xray config.json
4. 预览 config.json
5. 校验 config.json
6. 保存 config.json
7. 重启或 reload Xray 服务
8. 失败时恢复旧 config.json
9. 显示给 A 端填写的连接参数
```

## 3. 不做什么

为了保持项目轻量，第一版明确不做：

```text
多用户权限系统
注册 / 邀请 / 用户管理
订阅链接
机场面板能力
流量统计
限速
账单
审计日志
复杂 dashboard
Caddy 管理
证书管理
Xray Reverse / Bridge / Portal
sing-box
agent
多机同步
目标地址 ACL
复杂防火墙管理
```

## 4. 运行方式

后端使用：

```text
Python 3.11+
FastAPI
Jinja2 模板
普通 HTML + fetch
JSON 文件持久化
```

第一版不引入数据库。配置直接保存到：

```text
data/settings.json
```

生成的 Xray 配置保存到用户指定的 Xray 目录：

```text
<xray_path>/config.json
```

Xray 可执行文件默认约定为：

```text
<xray_path>/xray
```

例如：

```text
/opt/xray/
├── xray
└── config.json
```

## 5. Web 访问安全

因为这是个人工具，第一版不做完整账号体系。

推荐两种安全方式，默认使用第一种：

### 方式一：只监听本机

FastAPI 默认监听：

```text
127.0.0.1:18080
```

然后用户通过 SSH tunnel 或本机访问。

### 方式二：简单管理密码

如果需要公网访问，使用一个简单的管理 token：

```text
ADMIN_TOKEN=your-secret-token
```

前端请求时带 cookie 或 header。

第一版只需要单 token，不需要用户表。

## 6. 页面设计

第一版只做 4 个页面。

### 6.1 首页

显示：

```text
Xray 路径
config.json 路径
Xray 是否运行
当前启用的入站数量
最近一次校验结果
最近一次应用结果
```

按钮：

```text
生成预览
校验配置
保存配置
保存并重启 Xray
```

### 6.2 设置页

字段：

```text
Xray 目录
Xray 服务名
面板监听地址
面板监听端口
```

默认值：

```text
xray_path = /opt/xray
xray_service_name = xray
host = 127.0.0.1
port = 18080
```

Xray 路径逻辑：

```text
xray_bin = <xray_path>/xray
xray_config = <xray_path>/config.json
```

### 6.3 入站管理页

这是核心页面。

字段：

```text
名称
启用 / 禁用
监听地址
监听端口
协议：vless / vmess
UUID
mKCP header type
mKCP seed
mtu
tti
uplinkCapacity
downlinkCapacity
congestion
readBufferSize
writeBufferSize
```

默认值：

```text
listen = 0.0.0.0
protocol = vless
header type = none
mtu = 1350
tti = 20
uplinkCapacity = 20
downlinkCapacity = 100
congestion = false
readBufferSize = 2
writeBufferSize = 2
```

支持操作：

```text
新增
编辑
删除
启用 / 禁用
复制 A 端参数
```

### 6.4 配置预览页

显示最终生成的 Xray JSON。

按钮：

```text
复制 JSON
下载 JSON
校验 JSON
保存 JSON
保存并重启 Xray
```

## 7. B 端 Xray 配置生成规则

第一版生成完整 config.json，不依赖用户手写 JSON。

基础结构：

```json
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [],
  "outbounds": [
    {
      "tag": "direct",
      "protocol": "freedom",
      "settings": {}
    },
    {
      "tag": "blocked",
      "protocol": "blackhole",
      "settings": {}
    }
  ],
  "routing": {
    "rules": []
  }
}
```

每个启用的入站生成一个 Xray inbound。

## 8. VLESS over mKCP inbound 模板

```json
{
  "tag": "tunnel-in-1",
  "listen": "0.0.0.0",
  "port": 40000,
  "protocol": "vless",
  "settings": {
    "clients": [
      {
        "id": "UUID",
        "email": "tunnel-1"
      }
    ],
    "decryption": "none"
  },
  "streamSettings": {
    "network": "kcp",
    "security": "none",
    "kcpSettings": {
      "mtu": 1350,
      "tti": 20,
      "uplinkCapacity": 20,
      "downlinkCapacity": 100,
      "congestion": false,
      "readBufferSize": 2,
      "writeBufferSize": 2,
      "header": {
        "type": "none"
      },
      "seed": "your-seed"
    }
  }
}
```

## 9. VMess over mKCP inbound 模板

```json
{
  "tag": "tunnel-in-1",
  "listen": "0.0.0.0",
  "port": 40000,
  "protocol": "vmess",
  "settings": {
    "clients": [
      {
        "id": "UUID",
        "alterId": 0,
        "email": "tunnel-1"
      }
    ]
  },
  "streamSettings": {
    "network": "kcp",
    "security": "none",
    "kcpSettings": {
      "mtu": 1350,
      "tti": 20,
      "uplinkCapacity": 20,
      "downlinkCapacity": 100,
      "congestion": false,
      "readBufferSize": 2,
      "writeBufferSize": 2,
      "header": {
        "type": "none"
      },
      "seed": "your-seed"
    }
  }
}
```

## 10. routing 规则

每个 inbound 都走 `direct`：

```json
{
  "type": "field",
  "inboundTag": [
    "tunnel-in-1"
  ],
  "outboundTag": "direct"
}
```

这表示：

```text
A 端 dokodemo-door 指定目标地址和端口
B 端只负责接收连接并用 freedom 出站连接该目标
```

## 11. A 端参数展示

每个 B 端入站页面需要显示一段可复制信息：

```text
协议：vless
远端地址：B_PUBLIC_IP
远端端口：40000
UUID：xxxx
传输：mKCP
header type：none
seed：your-seed
mtu：1350
tti：20
uplinkCapacity：20
downlinkCapacity：100
congestion：false
readBufferSize：2
writeBufferSize：2
```

这里的 `B_PUBLIC_IP` 可以让用户手动填写，也可以留空，让用户自己复制时补上。

## 12. 校验流程

应用配置前必须校验。

流程：

```text
1. 根据当前面板配置生成 JSON
2. 写入临时文件：<xray_path>/.config.x-ui-test.json
3. 执行：<xray_path>/xray run -test -config <temp-file>
4. 返回 stdout / stderr
5. 校验成功才允许保存或重启
```

命令执行必须用 Python `subprocess.run([...])`，不能拼 shell 字符串。

正确：

```python
subprocess.run([xray_bin, "run", "-test", "-config", temp_config])
```

不要：

```python
subprocess.run(f"{xray_bin} run -test -config {temp_config}", shell=True)
```

## 13. 保存流程

保存 config.json 的流程：

```text
1. 生成新 config
2. 校验新 config
3. 备份旧 config.json：config.json.bak.时间戳
4. 写入临时文件：.config.x-ui.tmp
5. 原子替换 config.json
```

不能直接覆盖写入 config.json，避免写一半失败。

## 14. 重启 Xray 流程

第一版优先使用 systemd 服务方式，因为 B 端通常是服务运行。

设置项：

```text
xray_service_name = xray
```

重启命令：

```text
systemctl restart <xray_service_name>
```

状态命令：

```text
systemctl is-active <xray_service_name>
```

实现注意：

```text
不要让用户输入完整命令
只允许输入 service name
后端固定执行 systemctl restart / is-active
```

如果用户不使用 systemd，第二版再加 direct process 模式。

## 15. 保存并重启的回滚流程

```text
1. 生成新 config
2. xray run -test 校验
3. 备份旧 config.json
4. 写入新 config.json
5. systemctl restart xray
6. 如果 restart 成功：完成
7. 如果 restart 失败：恢复旧 config.json
8. 再尝试 systemctl restart xray
9. 返回失败日志
```

## 16. 文件结构计划

```text
b_client_xray/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── storage.py
│   ├── models.py
│   ├── xray_config.py
│   ├── xray_runtime.py
│   ├── routers/
│   │   ├── pages.py
│   │   ├── api_settings.py
│   │   ├── api_tunnels.py
│   │   └── api_xray.py
│   ├── templates/
│   │   ├── layout.html
│   │   ├── index.html
│   │   ├── settings.html
│   │   ├── tunnels.html
│   │   └── preview.html
│   └── static/
│       └── app.css
├── data/
│   └── .gitkeep
├── requirements.txt
├── README.md
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

## 17. 数据结构计划

`data/settings.json`：

```json
{
  "xray_path": "/opt/xray",
  "xray_service_name": "xray",
  "panel_host": "127.0.0.1",
  "panel_port": 18080,
  "public_address": "",
  "tunnels": [
    {
      "id": "tunnel-1",
      "name": "default",
      "enable": true,
      "listen": "0.0.0.0",
      "port": 40000,
      "protocol": "vless",
      "uuid": "",
      "kcp_header_type": "none",
      "kcp_seed": "",
      "kcp_mtu": 1350,
      "kcp_tti": 20,
      "kcp_uplink_capacity": 20,
      "kcp_downlink_capacity": 100,
      "kcp_congestion": false,
      "kcp_read_buffer_size": 2,
      "kcp_write_buffer_size": 2
    }
  ]
}
```

## 18. API 计划

```text
GET  /
GET  /settings
GET  /tunnels
GET  /preview

GET  /api/status
GET  /api/settings
POST /api/settings

GET  /api/tunnels
POST /api/tunnels
PUT  /api/tunnels/{id}
DELETE /api/tunnels/{id}
POST /api/tunnels/{id}/toggle

GET  /api/xray/config
POST /api/xray/validate
POST /api/xray/save
POST /api/xray/restart
POST /api/xray/apply
```

其中：

```text
/api/xray/apply = validate + backup + save + restart + rollback on failure
```

## 19. 实现顺序

### 阶段 1：项目骨架

```text
FastAPI app
Jinja2 模板
静态文件
settings.json 读写
首页
```

### 阶段 2：Xray 配置生成

```text
Tunnel 数据结构
VLESS inbound 生成
VMess inbound 生成
outbounds 生成
routing 生成
config 预览页面
```

### 阶段 3：Xray 校验和应用

```text
xray run -test
config.json 备份
原子保存
systemctl restart
失败回滚
状态显示
```

### 阶段 4：页面完善

```text
入站 CRUD 页面
复制 A 端参数
显示命令输出
基础错误提示
```

### 阶段 5：打包运行

```text
requirements.txt
启动脚本
systemd service 示例
README 使用说明
```

## 20. 第一版验收标准

满足以下条件即可认为第一版完成：

```text
1. 能通过 Web 添加一个 VLESS over mKCP 入站
2. 能生成 B 端完整 config.json
3. 生成的 config.json 能通过 xray run -test
4. 能保存 config.json
5. 能重启 Xray 服务
6. A 端 x-ui 使用页面显示的参数能连接 B 端
7. reload/restart 失败时旧 config.json 能恢复
```

## 21. 后续可选功能

第一版完成后，如果确实需要，再考虑：

```text
目标地址白名单
读取 Xray access/error log
更漂亮的 UI
单 token 登录
Windows 运行方式
非 systemd direct process 模式
导入已有 config.json
```

这些都不是第一版核心。
