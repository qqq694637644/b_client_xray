# b_client_xray

一个个人自用的 B 端 Xray 管理面板计划。

目标：用 Python FastAPI + 简单 Web 页面管理 B 端 Xray 的 VLESS/VMess over mKCP inbound，生成、校验、保存并应用 `config.json`，让 A 端 x-ui 可以连接过来。

完整计划见：[`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)

## 第一版范围

```text
只做个人自用
只管理 B 端 Xray
只生成 inbound over mKCP + freedom outbound + routing
不做订阅、不做多用户、不做流量统计、不做复杂 dashboard
```

## 第一版核心功能

```text
1. 配置 Xray 目录
2. 管理 B 端 mKCP 入站
3. 生成完整 Xray config.json
4. 预览配置
5. xray run -test 校验配置
6. 备份并保存 config.json
7. systemctl restart xray
8. 失败时恢复旧 config.json
9. 显示给 A 端填写的连接参数
```
