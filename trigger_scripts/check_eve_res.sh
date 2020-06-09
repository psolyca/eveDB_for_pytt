#!/bin/bash

link="https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
daterev=$(curl -s -v -X HEAD $link 2>&1 | grep '< Last-Modified:' | awk -F ':' '{print $2":"$3":"$4}')
currentrev=$(echo $daterev | xargs -0 date +"%s" -d)
echo -e "Current SDE revision on $daterev\n" \
"\tTimestamp : $currentrev"
gitrev=$(curl https://api.github.com/repos/psolyca/eveDB_for_pytt/commits/master 2>&1 | grep '"message"' | awk -F\" '{print $4}')
if [[ $gitrev == *"$currentrev"* ]]
then
    echo "Already lastest SDE commited"
    exit
fi
echo 'Latest commit was :' $gitrev
echo 'Triggering build of database'

body='{
"request": {
"branch":"master"
}}'

curl -s -X POST \
   -H "Content-Type: application/json" \
   -H "Accept: application/json" \
   -H "Travis-API-Version: 3" \
   -H "Authorization: token xxxxxxxxxxxxxxxxx" \
   -d "$body" \
   https://api.travis-ci.com/repo/psolyca%2FeveDB_for_pytt/requests
