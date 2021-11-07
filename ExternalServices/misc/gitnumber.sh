#!/bin/sh
pushd ../.. > /dev/null
version_id=`git rev-list --branches main | wc -l`
popd > /dev/null
echo "VERSION_POSTFIX=\"$version_id\"" > "../version_info.py"