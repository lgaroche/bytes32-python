import time
import datetime
import json

def fetch_logs(w3, start_block, event, handle_logs, block_range=17280):
  latest = w3.eth.get_block('latest')
  print(f"will start at block={start_block}, latest={latest.number}")
  block_range = min(latest.number - start_block, block_range)

  while start_block < latest.number:
    try:
      if start_block + block_range > latest.number:
        # update latest block number
        latest = w3.eth.get_block('latest')
        print(f"latest block number: {latest.number}")

      end_block = min(latest.number, start_block + block_range)
      before = time.time()
      print(f"start_block={start_block} end_block={end_block}")
      logs = event.getLogs(fromBlock=start_block, toBlock=end_block)
      after = time.time()
      response_time = after - before
      
      if len(logs) > 0:
        last = w3.eth.get_block(logs[-1].blockNumber)
        delta = datetime.timedelta(seconds=after - last.timestamp)
        print(f"got {len(logs)} logs in ({round(response_time)}s) (up to block: {end_block} {delta.days} days ago)")
        handle_logs(logs)

      start_block = end_block + 1

      if response_time > 5:
        block_range = round(block_range/2)
        print(f"long reponse ({round(response_time)}s), reducing block_range to: {block_range}")
      elif response_time < 1:
        block_range += round(block_range/10)
        print(f"short reponse ({response_time}s), increasing block_range to: {block_range}")

    except json.decoder.JSONDecodeError as e:
      block_range = round(block_range/2)
      print(f"possible timeout, reducing block range to: {block_range}")
    time.sleep(0.5)

  print("start monitoring new logs")
  start_block = latest.number + 1
  while True:
    latest = w3.eth.get_block('latest')
    print(f"latest block number: {latest.number}")
    if latest.number > start_block:
      logs = event.getLogs(fromBlock=start_block, toBlock=latest.number)
      if len(logs) > 0:
        print(f"got {len(logs)} log(s) in the last {latest.number - start_block} block(s)")
        handle_logs(logs)
      start_block = latest.number + 1
    time.sleep(5)