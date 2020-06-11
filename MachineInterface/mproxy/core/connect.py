"""Helper for creating connections to AMQP servers"""


def aio_pika_connect_params(config, keypath: str = None) -> dict:
    """Return a dict keyword arguments that can be passed to
    aio_pika.connect
    """
    if keypath is None:
        mq_conf = config
    else:
        mq_conf = config.get(keypath)    

    return {        
        "host": mq_conf["hostname"],        
    }
