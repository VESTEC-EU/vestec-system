#!/bin/sh
cd $1
git rev-list --all | wc -l