#!/bin/bash

su - ${DASH_USER} << EOF
cd Automator
./create_projects.py -p tests/github_test.conf -d tests -s -n GitHubTest  --dbuser=root --dbpasswd=${ROOT_DBPASSWD}
sed -i tests/GitHubTest/conf/main.conf \
    -e "s/db_password =[ ]*$/db_password = rootpw/" \
    -e "s/# backend_user = miningbitergia/backend_user = ${GITHUB_USER}/" \
    -e "s/# backend_password = passwd/backend_password =  ${GITHUB_PASSWD}/"
./launch.py -d /home/automator/Automator/tests/GitHubTest
cd /home/automator/Automator/tests/GitHubTest/tools/VizGrimoireJS
make
EOF

rm -rf /var/www/github
ln -s /home/automator/Automator/tests/GitHubTest/tools/VizGrimoireJS/browser /var/www/github



# backend_password = passwd