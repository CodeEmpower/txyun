# txyun

# 腾讯云轻量服务器秒杀脚本

腾讯云轻量应用服务器 **4核4G3M 38元/年** 异步高并发秒杀抢购脚本。

活动页面: https://cloud.tencent.com/act/pro/featured-202604

## 使用步骤

### 1. 获取 Cookie

1. 浏览器打开 [腾讯云活动页](https://cloud.tencent.com/act/pro/featured-202604) 并**登录**
2. 按 `F12` 打开开发者工具
3. 切换到 `Network` 面板，刷新页面
4. 随便点击一个请求，在 `Headers` 中找到 `Cookie` 字段
5. 复制完整的 Cookie 字符串

> Cookie 中必须包含 `skey` 字段，脚本依赖它计算 CSRF Token。如果找不到 `skey`，尝试访问腾讯云控制台页面再查看。

### 2. 填写配置

打开 `tencent_server_seckill.py`，修改顶部的参数:

```python
# 浏览器 Cookie 字符串 (粘贴到这里)
COOKIES = "your_cookie_string_here"

# 目标抢购时间, 格式 "HH:MM:SS"
# 上午场: "10:00:00"  下午场: "15:00:00"
# 设为 None 则立即抢购 (不等待)
TARGET_TIME = "15:00:00"

# 提前多少毫秒开始发请求 (补偿网络延迟, 建议 200-500ms)
ADVANCE_MS = 300

# 每个地域并发请求数 (总并发 = 3 地域 × 此值)
CONCURRENCY_PER_REGION = 20
```

### 3. 运行脚本

```bash
python tencent_server_seckill.py
```

脚本会自动:
1. 校准服务器时间 (采样 5 次取最优)
2. 显示倒计时等待到目标时间
3. 提前 `ADVANCE_MS` 毫秒开始并发请求
4. 抢购成功后自动停止
<img width="509" height="571" alt="image" src="https://github.com/user-attachments/assets/b5a53294-1520-4ddc-a755-892fb9039273" />


## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `COOKIES` | `""` | 浏览器 Cookie 字符串 |
| `TARGET_TIME` | `"15:00:00"` | 目标抢购时间，`None` 为立即抢购 |
| `ADVANCE_MS` | `300` | 提前发请求的毫秒数，补偿网络延迟 |
| `CONCURRENCY_PER_REGION` | `20` | 每个地域的并发数，总并发 = 3 × 此值 |


### 服务器时间校准

启动时向腾讯云 API 发送 5 次请求，通过两种方式获取服务器时间:
- **响应头 `Date`**: HTTP 标准时间戳
- **响应体 `nowTime`**: API 返回的毫秒时间戳

取 5 次采样中延迟最小的偏移量，补偿本地时钟误差。

### 并发策略

- 同时向 3 个地域 (广州/上海/北京) 发送抢购请求
- 使用 `asyncio.Semaphore` 控制总并发数，避免本地端口耗尽
- 每轮请求间隔 50ms，循环直到抢购成功
- CSRF 失效时自动重算
## 免责声明

本脚本仅供学习交流使用。使用本脚本产生的一切后果由使用者自行承担。
