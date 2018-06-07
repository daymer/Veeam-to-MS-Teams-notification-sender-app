# Version: 1.0
# docker build -t veeam_to_teams:1.0 -f /home/drozhd/veeam_to_teams/Dockerfile /home/drozhd/veeam_to_teams
FROM python:3.6.2
MAINTAINER Dmitry Rozhdestvenskiy <dremsama@gmail.com>
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get -y install locales
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
RUN apt-get -y install apt-transport-https freetds-dev unixodbc-dev git
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/8/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get -y update && ACCEPT_EULA=Y apt-get install msodbcsql
RUN mkdir /veeam_to_msteams
RUN git clone https://github.com/daymer/Veeam-to-MS-Teams-notification-sender-app /veeam_to_msteams
RUN pip install --upgrade pip
RUN pip install -r /veeam_to_msteams/requirements.txt
RUN mkdir /var/log/veeam_to_msteams/
ADD configuration.py /veeam_to_msteams/
RUN chmod +x /veeam_to_teams/launch_veeam_to_msteams.sh
CMD ["/bin/bash", "/Elisa/launch_veeam_to_msteams.sh"]