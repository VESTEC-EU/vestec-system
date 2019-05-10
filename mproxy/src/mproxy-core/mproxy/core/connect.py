"""Helper for creating connections to AMQP servers"""


def aio_pika_connect_params(config, keypath: str = None) -> dict:
    """Return a dict keyword arguments that can be passed to
    aio_pika.connect
    """
    if keypath is None:
        mq_conf = config
    else:
        mq_conf = config.get(keypath)

    try:
        pw = mq_conf["password"]
    except KeyError:
        pw_file = mq_conf["password_file"]
        with open(pw_file) as f:
            pw = f.read()
        pass

    return {
        "login": mq_conf["username"],
        "password": pw,
        "host": mq_conf["hostname"],
        "port": mq_conf.get("port", 5672),
        "virtualhost": mq_conf.get("vhost", "/"),
    }
