#!/bin/bash

link="https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
daterev=$(curl -s -v -X HEAD $link 2>&1 | grep '< Last-Modified:' | awk -F ':' '{print $2":"$3":"$4}')
currentrev=$(echo $daterev | xargs -0 date +"%s" -d)
echo 'Current SDE revision of ' $daterev ' -> ' $currentrev
if [[ $(git log -1 --pretty=%B) == *"$currentrev"* ]]
then
    echo "Already lastest SDE commited"
    exit
fi
echo 'Latest commit was :' $(git log -1 --pretty=%B)
echo 'Building database files for revision' $currentrev
git config --global user.email "$GH_USER_EMAIL"
git config --global user.name "$GH_USER_NAME"
git remote add origin-ssh git@github.com:$GH_REPO
mkdir -p resources
python3 db_create.py
git add resources/eve.db
git commit -m "Up to date DB with SDE $currentrev"
git checkout -b temp
git checkout -B $TRAVIS_BRANCH temp
git push --quiet --set-upstream origin-ssh $TRAVIS_BRANCH