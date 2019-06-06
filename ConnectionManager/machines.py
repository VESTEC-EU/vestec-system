machines ={}

machines["ARCHER"]  = {
    "host": "login.archer.ac.uk",
    "username": "bpvestec",
    "SSHkey": "rsa_cron",
    "basedir": "/work/d170/d170/bpvestec/",
    "available_nodes": 4920,
    "cores_per_node": 24,
    "main_queue": "standard",
    "queues": [
        {
            "queue_name": 'standard',
            "max_nodes": 4920,
            "min_time": "00:01:00",
            "max_time": "24:00:00"
        },
        {
            "queue_name": 'long',
            "max_nodes": 256,
            "min_time": "24:00:00",
            "max_time": "48:00:00"
        },
        {
            "queue_name": 'short',
            "max_nodes": 8,
            "min_time": "00:01:00",
            "max_time": "00:20:00"
        },
        {
            "queue_name": 'low',
            "max_nodes": 512,
            "min_time": "00:01:00",
            "max_time": "03:00:00"
        },
        {
            "queue_name": 'largemem',
            "max_nodes": 376,
            "min_time": "00:01:00",
            "max_time": "48:00:00"
        },
        {
            "queue_name": 'serial',
            "max_nodes": 1,
            "min_time": "00:01:00",
            "max_time": "24:00:00"
        }
    ]
}

machines["CIRRUS"] = {
    "host": "cirrus.epcc.ed.ac.uk",
    "username": "bpcirrus",
    "SSHkey": "rsa_cirrus",
    "basedir": "/lustre/home/z04/bpcirrus/vestec",
    "available_nodes": 280,
    "cores_per_node": 36,
    "main_queue": "workq",
    "queues": [
        {
            "queue_name": 'workq',
            "max_nodes": 70,
            "min_time": "00:01:00",
            "max_time": "96:00:00"
        },
        {
            "queue_name": 'indy',
            "max_nodes": 15,
            "min_time": "00:01:00",
            "max_time": "336:00:00"
        },
        {
            "queue_name": 'large',
            "max_nodes": 280,
            "min_time": "00:01:00",
            "max_time": "48:00:00"
        }
    ]
}
