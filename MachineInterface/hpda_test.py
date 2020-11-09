#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  9 09:55:05 2020

@author: kont_ma
"""

import asyncio
from mproxy.client import Client

async def get_job_directory_listing(machine_name, directory_name):
    client = await Client.create(machine_name)
    return await client.ls(directory_name)

if __name__=='__main__':
    print(asyncio.run(get_job_directory_listing("HPDA", ".")))
