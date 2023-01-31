import traceback
import asyncio
import json
import aiohttp
import os
import time
import hashlib
import parse_thread as parse
import aria2p

# PROXY = None
PROXY = "http://127.0.0.1:7890"
TIMEOUT = 300

CACHE_FOLDER = "E:/mirror/cache" # 缓存目录

async def _get_json(url: str, timeout : int = TIMEOUT, no_proxy: bool =False):
    _i = 0 # retry times
    if no_proxy:
        proxy = None
    else:
        proxy = PROXY
    while _i < 3:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
                async with sess.get(url=url, proxy=proxy) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 404:
                        return resp.status
        except Exception:
            _i += 1
            traceback.print_exc()

def check_hash(hash: str, path: str):
    if len(hash) == 40:
        hash_ = hashlib.sha1()
    elif len(hash) == 32:
        hash_ = hashlib.md5()
    else:
        raise ValueError("Unknown hash type")

    with open(path, "rb") as f:
        hash_.update(f.read())
        return hash_.hexdigest() == hash

async def get_file(url: str, name: str, sem: asyncio.Semaphore, timeout : int = TIMEOUT):
    async with sem:
        print(f'Downloading: {url}')
        _i = 0 # retry times
        while _i < 3:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
                    async with sess.get(url=url, proxy=PROXY) as resp:
                        if resp.status == 200:
                            with open(name, "wb") as f:
                                async for chunk in resp.content.iter_chunked(1024):
                                    f.write(chunk)
                            print(f'Downloaded: {name}')
                            return
                        elif resp.status == 400:
                            print(f'404 Not Found {url}')
                            break
            except Exception as e:
                _i += 1
                print(f'Get file error: {url} {e}')
                traceback.print_exc()

async def download(url: str, name: str, sem: asyncio.Semaphore):
    async with sem:
        name = os.path.join(CACHE_FOLDER, name)
        if not os.path.exists(os.path.dirname(name)):
            os.makedirs(os.path.dirname(name))
        await get_file(url, name, sem)

def get_results(): # 添加新的镜像源
    print("正在获取数据...wait a moment, plz...")
    results = []
    results.extend(parse.vanilla(source="mcbbs"))
    results.extend(parse.papermc())
    # results.extend(parse.spigot())
    results.extend(parse.arclight())
    results.extend(parse.bungeecord())
    results.extend(parse.floodgate())
    results.extend(parse.catserver())
    results.extend(parse.geyser())
    results.extend(parse.lightfall())
    results.extend(parse.mohist())
    results.extend(parse.nukkitx())
    results.extend(parse.pocketmine())
    results.extend(parse.pufferfish())
    results.extend(parse.sponge())
    results.extend(parse.forge(sourse="mcbbs"))
    
    with open("result.json", "w") as res:
        json.dump(results, res)
    print("获取数据完成，已缓存信息至 result.json")
    # print("从本地读取数据...")
    # with open("result.json") as res:
    #     results = json.load(res)
    return results

def main():
    results = get_results()
    print(f"共计 {len(results)} 待处理")

    # For asyncio
    # tasks = []
    # sem = asyncio.Semaphore(64) # 限制 16 并发

    # for result in results:
    #     # 校验文件是否存在且正确
    #     if os.path.exists(os.path.join(CACHE_FOLDER, result["name"])):
    #         if "md5" in result or "sha1" in result:
    #             if "md5" in result:
    #                 hash = result["md5"]
    #             else:
    #                 hash = result["sha1"]
    #             hash_result = check_hash(hash, os.path.join(CACHE_FOLDER, result["name"]))
    #             if hash_result:
    #                 print(f'Cached: {result["name"]}')
    #                 continue # 跳过已存在的文件
    #         os.remove(os.path.join(CACHE_FOLDER, result["name"])) # 删除不确定/不完整文件
    #     tasks.append(asyncio.create_task(download(result["url"], result["name"], sem)))
    # await asyncio.gather(*tasks)

    # For aria2
    client = aria2p.Client()
    api = aria2p.API(client=client)
    client.purge_download_result()
    dls = []
    for result in results:
        complete_path = os.path.join(CACHE_FOLDER, result["name"])
        if os.path.exists(complete_path):
            if "md5" in result or "sha1" in result:
                hash = result["md5"] if "md5" in result else result["sha1"]
                if check_hash(hash, complete_path):
                    print(f'Cached: {result["name"]}')
                    continue
            os.remove(complete_path)
        dl = api.add(uri=result["url"], options={"dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FOLDER, os.path.split(result["name"])[0]), "out": os.path.split(result["name"])[1]})
        dls.append(dl)

    print(f"共计 {len(dls)} 个文件待下载")
    while True:
        status = client.get_global_stat()
        print(status)
        if status["numActive"] == '0':
            dls = api.get_downloads([dl[0].gid for dl in dls]) # update dls
            failed_count = 0
            for dl in dls:
                if dl.has_failed:
                    print(f'Failed: {dl.name}')
                    failed_count += 1
            print(f"已完成所有下载，{failed_count} 个下载失败")
            break
        time.sleep(0.5)

if __name__ == "__main__":
    get_results()