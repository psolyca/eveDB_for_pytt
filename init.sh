#!/bin/bash

link="https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
resdate=$(curl -s -v -X HEAD $link 2>&1 | grep '< Last-Modified:' | awk -F ':' '{print $2":"$3":"$4}')
resstamp=$(echo $resdate | xargs -0 date +"%s" -d)
echo -e "SDE revision of $resdate\n" \
"\tTimestamp : $resstamp"
repstamp=$(cat version)
if [[ $repstamp == *"$resstamp"* ]]
then
    echo "Already lastest SDE commited"
    exit
fi
echo 'Latest commit was :' $repstamp
echo 'Building database files'
git config --global user.email "$GH_USER_EMAIL"
git config --global user.name "$GH_USER_NAME"
git remote add origin-ssh git@github.com:$GH_REPO
mkdir -p resources
python3 db_create.py
git add resources/eve.db
echo $resstamp > version
git add version
git commit -m "Up to date DB with SDE $resstamp"
git checkout -b temp
git checkout -B $TRAVIS_BRANCH temp
git push --quiet --set-upstream origin-ssh $TRAVIS_BRANCH