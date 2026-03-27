from concurrent.futures import ThreadPoolExecutor, as_completed

executor = ThreadPoolExecutor(max_workers=20)


def run_parallel(tasks):
    futures = [executor.submit(fn) for fn in tasks]

    results = []
    for f in as_completed(futures):
        try:
            results.append(f.result())
        except Exception as e:
            print("任务异常:", e)

    return results
