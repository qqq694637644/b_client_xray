# b_client_xray

一个个人自用的 Windows B 端 Xray 可视化管理面板。

目标：用 Python FastAPI + 简单 Web 页面管理 **多个 B 端 Xray 隧道**。用户在网页表格和表单里新增、编辑、启用、禁用、删除隧道；后端自动把多个隧道合并生成一个完整的 `config.json`，再负责校验、保存、重启 Windows Xray 服务和失败回滚。

完整计划见：[`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)

## 第一版范围

```text
只做个人自用
只支持 Windows
只支持你提供的 Xray 26.3.27 配置字段
只管理 B 端 Xray
支持多个隧道
网页可视化 CRUD 配置
后端自动生成一个完整 config.json
不要求用户手写或拼接裸 JSON
不做订阅、不做多用户、不做流量统计、不做复杂 dashboard
```

## 第一版核心功能

```text
1. 配置 Xray 目录和 Windows 服务名
2. 默认使用 <xray_path>\\xray.exe
3. 默认使用 <xray_path>\\config.json
4. 用网页表格管理多个 B 端 mKCP 隧道
5. 每个隧道用表单配置协议、端口、UUID、mKCP 参数
6. 后端自动把所有启用隧道合成一个 Xray config.json
7. 提供 config.json 预览，但预览不是主要编辑方式
8. xray.exe run -test 校验配置
9. 备份并保存 config.json
10. sc.exe stop/start 重启 Windows Xray 服务
11. 失败时恢复旧 config.json
12. 每个隧道显示给 A 端填写的连接参数
```

## 直连与 Portal

- `direct` 保持原有行为：B 监听 VMess/VLESS mKCP 端口，A 主动连接 B。
- `portal` 用于 B 无公网 IP：B 通过 VMess over mKCP 主动连接 A 的 Portal UDP 端口，并生成 Xray `reverse.bridges`。
- Portal 模式固定 `VMess + alterId=0 + security=auto`，不启用额外 outbound mux。
- Portal 的目标地址和端口由 A 的 dokodemo-door 请求携带，B 的 Bridge 路由到 `direct` 后执行；`127.0.0.1` 表示 B 本机。入口网络可选 TCP、UDP 或 TCP+UDP。
- A、B 两端的 UUID、mKCP、FinalMask 参数必须手工保持一致；实现按 Xray-core v26.3.27（提交 `d2758a023cd7f4174a5a5fa4ff66e487d4342ba0`）生成配置。
- 网页面板可以手工启动，但“保存并应用”通过 `sc.exe` 管理 Xray，因此 `xray.exe` 必须注册为 Windows 服务，服务名与设置页一致。启动后会等待服务进入 `RUNNING` 并稳定保持 2 秒；失败时恢复旧配置。

## Portal smoke test

仓库保留了可复现的双实例测试，使用指定的 v26.3.27 二进制启动 A Portal、B Bridge 和本地 TCP/UDP echo，并验证 B 重启与 A 重启后的自动重连：

```powershell
python scripts/smoke_portal.py --xray C:\xray\xray.exe
```

Linux CI 会从精确提交 `d2758a023cd7f4174a5a5fa4ff66e487d4342ba0` 构建 Xray 后运行同一脚本。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

默认访问：

```text
http://127.0.0.1:18080
```
