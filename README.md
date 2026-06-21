# Agently.top

每日 AI / 开源 / 科技信息聚合 · 中文智能摘要 · 卡片式资讯流 · 微信公众号自动发布

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?style=flat-square&logo=github)](https://github.com/yunlongwen/agently.top)
[![GitHub forks](https://img.shields.io/github/forks/yunlongwen/agently.top?style=flat-square)](https://github.com/yunlongwen/agently.top/fork)
[![GitHub stars](https://img.shields.io/github/stars/yunlongwen/agently.top?style=flat-square)](https://github.com/yunlongwen/agently.top/stargazers)

线上地址：[https://agently.top](https://agently.top)

---

## 它是什么

Agently.top 每天自动抓取 9 个信息源的中英文科技与 AI 资讯，通过 AI 生成中文摘要，以卡片流形式呈现，并支持邮件订阅与微信公众号自动发布。

---

## 主要特性

- **每日自动采集**：9 大源独立容错，单一源失败不影响整体输出
- **AI 中文摘要**：聚焦 AI / 软件工程师关注点
- **邮件推送与订阅**：按调度时间自动发送每日摘要，访客可订阅
- **微信公众号自动发布**：每日精选自动入库草稿箱
- **Web + API**：Vue 3 卡片流前端，FastAPI 只读接口，RSS 输出
- **访问统计**：内置轻量统计，UV/PV 自查

---

## 快速开始

```bash
# 安装依赖
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY、REDIS_URL 等必要配置

# 跑一次采集
python3 main.py

# 启动 API 服务
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
```

完整部署、环境变量与运维说明见 [`docs/setup-and-config.md`](docs/setup-and-config.md)。

---

## 关注微信公众号

扫码关注 **Agently.top** 公众号，每日获取 AI 开发资讯：

![微信公众号二维码](qrcode_for_agently.jpg)

---

## 相关文档

- [部署与配置指南](docs/setup-and-config.md)
- [RSS/API 接口说明](docs/rss-api-guide.md)
- [环境变量示例](.env.example)

---

## License

[MIT](LICENSE)
