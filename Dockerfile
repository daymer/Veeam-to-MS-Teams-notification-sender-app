# Version: 2.0
# docker build -t veeam_to_msteams:2.0 -f /home/drozhd/veeam_to_teams/Dockerfile /home/drozhd/veeam_to_teams
FROM python:3.6.2
MAINTAINER Dmitry Rozhdestvenskiy <dremsama@gmail.com>
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils apt-transport-https freetds-dev unixodbc-dev git \
    && apt-get -y install locales \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/8/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get -y update && ACCEPT_EULA=Y apt-get install msodbcsql \
    && mkdir /veeam_to_msteams/ \
    && git clone https://github.com/daymer/Veeam-to-MS-Teams-notification-sender-app /veeam_to_msteams \
    && pip install --upgrade pip \
    && pip install -r /veeam_to_msteams/requirements.txt \
    && mkdir /var/log/veeam_to_msteams/ \
    && chmod +x /veeam_to_msteams/launch_veeam_to_msteams.sh
ADD configuration.py /veeam_to_msteams/
CMD ["/bin/bash", "/veeam_to_msteams/launch_veeam_to_msteams.sh"]