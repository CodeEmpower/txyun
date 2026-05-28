"""
腾讯云 4核4G3M 轻量服务器 38元/年 秒杀脚本 (异步高并发版)
活动页面: https://cloud.tencent.com/act/pro/featured-202604
抢购接口: POST https://act-api.cloud.tencent.com/dianshi/do-goods
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import aiohttp

# ===================== 需要填写的参数 =====================

# 浏览器 Cookie 字符串
# 获取方式: 浏览器 F12，然后刷新一下，找一个有cookie请求，把标头的cookie的所有的值粘贴到下方
COOKIES = ""
# 目标抢购时间, 格式 "HH:MM:SS", 设为 None 则立即抢购
# 上午场: "10:00:00"  下午场: "15:00:00"
TARGET_TIME = "10:00:00"

# 提前多少毫秒开始发请求 (补偿网络延迟, 建议 200-500ms)
ADVANCE_MS = 300

# 每个地域并发请求数 (总并发 = 地域数 × 每地域并发数)
CONCURRENCY_PER_REGION = 20

# ===========================================================

# ===================== 秒杀商品配置 ========================

ACTIVITY_ID = 162634773874417
GOODS_ACT_ID = "1784747698901873"

# ===========================================================

_server_offset = 0.0


def compute_csrf(skey: str) -> str:
    """计算 CSRF Token (腾讯云 Djb2 Hash 算法)"""
    if not skey:
        return ""
    n = 5381
    for ch in skey:
        n += (n << 5) + ord(ch)
    return str(2147483647 & n)


def parse_cookies(cookies_str: str) -> dict:
    """解析 cookie 字符串为字典"""
    cookies = {}
    for item in cookies_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


async def sync_server_time(session: aiohttp.ClientSession, csrf: str) -> float:
    """校准服务器时间, 返回本地时钟偏移(秒)"""
    global _server_offset
    url = "https://act-api.cloud.tencent.com/dianshi/query-seckill-by-date"
    headers = {"X-Csrf-Token": csrf}

    best_offset = float('inf')
    for i in range(5):
        local_before = time.time()
        try:
            async with session.post(url, json={
                "activity_id": ACTIVITY_ID,
                "preview": 0,
                "seckill_type": "block",
                "goods_type": "goods",
                "days": 2,
            }, headers=headers) as resp:
                local_after = time.time()
                server_date = resp.headers.get("Date") or resp.headers.get("date")
                if server_date:
                    server_time = parsedate_to_datetime(server_date).timestamp()
                    local_mid = (local_before + local_after) / 2
                    offset = server_time - local_mid
                    latency = (local_after - local_before) / 2
                    if abs(offset) < abs(best_offset):
                        best_offset = offset
                    print(f"    采样 {i+1}: 偏移 {offset*1000:+.0f}ms, 延迟 {latency*1000:.0f}ms")

                try:
                    data = await resp.json()
                    now_time = data.get("data", {}).get("nowTime") or data.get("nowTime")
                    if now_time:
                        server_ts = now_time / 1000
                        local_mid = (local_before + local_after) / 2
                        offset = server_ts - local_mid
                        if abs(offset) < abs(best_offset):
                            best_offset = offset
                        print(f"    采样 {i+1} (nowTime): 偏移 {offset*1000:+.0f}ms")
                except Exception:
                    pass
        except Exception as e:
            print(f"    采样 {i+1} 失败: {e}")
        await asyncio.sleep(0.2)

    if best_offset != float('inf'):
        _server_offset = best_offset
        print(f"[*] 服务器时间校准完成: 本地时钟偏移 {_server_offset*1000:+.0f}ms")
    else:
        _server_offset = 0
        print("[!] 时间校准失败, 使用本地时间")
    return _server_offset


def get_server_now() -> datetime:
    return datetime.now() + timedelta(seconds=_server_offset)


async def wait_until(target_time: str):
    """等待到指定时间, 提前 ADVANCE_MS 毫秒开始发请求"""
    now = get_server_now()
    target = datetime.strptime(target_time, "%H:%M:%S").replace(
        year=now.year, month=now.month, day=now.day
    )
    advance = timedelta(milliseconds=ADVANCE_MS)
    target_adjusted = target - advance

    if now >= target_adjusted:
        target = target + timedelta(days=1)
        target_adjusted = target - advance
        print(f"[*] 目标时间已过, 等到明天 {target.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"[*] 目标时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"[*] 提前 {ADVANCE_MS}ms 发请求, 实际触发: {target_adjusted.strftime('%H:%M:%S.%f')[:-3]}")

    while True:
        now = get_server_now()
        if now >= target_adjusted:
            break
        remaining = target_adjusted - now
        total_secs = int(remaining.total_seconds())
        if total_secs < 0:
            break
        hours, remainder = divmod(total_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        if total_secs <= 10:
            print(f"\r[*] 倒计时: {remaining.total_seconds():.3f}s  ", end="", flush=True)
        else:
            print(f"\r[*] 倒计时: {hours:02d}:{minutes:02d}:{seconds:02d}  ", end="", flush=True)
        await asyncio.sleep(0.05 if total_secs <= 10 else 0.5)

    print(f"\n[!] 时间到 ({get_server_now().strftime('%H:%M:%S.%f')[:-3]}), 开始抢购!")


def build_payload(region_id: int) -> dict:
    return {
        "activity_id": ACTIVITY_ID,
        "agent_channel": {
            "fromChannel": "",
            "fromSales": "",
            "isAgentClient": False,
            "fromUrl": "https://cloud.tencent.com/act/pro/featured-202604"
        },
        "business": {
            "id": 22755,
            "from": "lightningDeals"
        },
        "goods": [
            {
                "act_id": GOODS_ACT_ID,
                "type": "bundle_budget_mc_lg4_01",
                "goods_param": {
                    "BlueprintId": "LINUX_UNIX",
                    "area": 1,
                    "ddocUnionConnect": 0,
                    "goodsNum": 1,
                    "imageId": "lhbp-eqora508",
                    "scenario": "0",
                    "timeSpanUnit": "12m",
                    "zone": "",
                    "regionId": region_id,
                    "type": "bundle_budget_mc_lg4_01"
                }
            }
        ],
        "preview": 0
    }


async def do_buy(session: aiohttp.ClientSession, region_id: int, csrf: str, sem: asyncio.Semaphore):
    async with sem:
        payload = build_payload(region_id)
        headers = {"X-Csrf-Token": csrf}
        try:
            async with session.post(
                "https://act-api.cloud.tencent.com/dianshi/do-goods",
                json=payload,
                headers=headers,
                ssl=False,
            ) as resp:
                result = await resp.json()
                code = result.get("code")
                msg = result.get("msg", "")[:100]
                ts = get_server_now().strftime("%H:%M:%S.%f")[:-3]
                region_map = {1: "广州", 4: "上海", 8: "北京"}
                name = region_map.get(region_id, str(region_id))

                if code == 0:
                    print(f"\n[{ts}] 抢购成功! 地域: {name}")
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return True

                print(f"[{ts}] {name}  code={code}  {msg}")
                return False
        except Exception as e:
            ts = get_server_now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{ts}] {region_id} 异常: {e}")
            return False


async def main():
    if not COOKIES:
        print("=" * 50)
        print("请先设置 COOKIES!")
        print("步骤:")
        print("1. 浏览器打开活动页面并登录腾讯云")
        print("2. F12 > Application > Cookies > cloud.tencent.com")
        print("3. 复制所有 cookie 粘贴到脚本顶部 COOKIES 变量")
        print("=" * 50)
        return

    cookies = parse_cookies(COOKIES)
    skey = cookies.get("skey", "") or cookies.get("p_skey", "")
    csrf = compute_csrf(skey)
    print(f"[*] skey: {skey[:15]}..." if skey else "[!] skey 为空, 请检查 Cookie")
    print(f"[*] CSRF: {csrf}")

    if not skey:
        print("[!] 未找到 skey, 无法计算 CSRF, 请更新 Cookie")
        return

    region_ids = [1, 4, 8]
    total_concurrency = len(region_ids) * CONCURRENCY_PER_REGION

    connector = aiohttp.TCPConnector(limit=total_concurrency, limit_per_host=total_concurrency)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        # 校准服务器时间
        print("\n[*] 校准服务器时间...")
        await sync_server_time(session, csrf)

        # 等待目标时间
        if TARGET_TIME:
            await wait_until(TARGET_TIME)

        # 开始并发抢购
        print(f"\n{'=' * 50}")
        print(f"[*] 目标: 轻量应用服务器 4核4G3M 38元/年")
        print(f"[*] 总并发数: {total_concurrency}")
        print(f"[*] 策略: 异步并发 do-goods 直接下单")
        print(f"{'=' * 50}\n")

        sem = asyncio.Semaphore(total_concurrency)

        while True:
            tasks = []
            for rid in region_ids:
                for _ in range(CONCURRENCY_PER_REGION):
                    tasks.append(do_buy(session, rid, csrf, sem))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            success = sum(1 for r in results if r is True)
            if success > 0:
                print(f"\n[SUCCESS] 抢购成功 {success} 个!")
                return

            # CSRF 失效自动重算
            if any("CSRF" in str(r) for r in results if isinstance(r, dict)):
                csrf = compute_csrf(skey)

            await asyncio.sleep(0.05)


if __name__ == "__main__":
    asyncio.run(main())
