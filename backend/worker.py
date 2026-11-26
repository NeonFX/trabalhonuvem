"""Processo independente de monitoramento periódico."""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import time
import db
from probe import check_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('worker')


def check_target(target):
    result = check_url(target['url'])
    db.save_check(target['id'], result)
    log.info('monitor=%s online=%s status=%s latency=%sms', target['id'], result.online, result.status_code, result.latency_ms)


def run_cycle():
    targets = db.targets()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(check_target, targets):
            pass


if __name__ == '__main__':
    interval = max(5, int(os.environ.get('CHECK_INTERVAL', '15')))
    log.info('Worker iniciado; intervalo de %ss após cada ciclo', interval)
    while True:
        try:
            run_cycle()
        except Exception:
            log.exception('Falha no ciclo; haverá nova tentativa')
        time.sleep(interval)
