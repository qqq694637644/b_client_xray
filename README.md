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
