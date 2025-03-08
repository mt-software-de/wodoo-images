FROM ubuntu:20.04
ARG ODOO_VERSION
MAINTAINER marc@itewimmer.de
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update --fix-missing && \
apt-get install \
	-y \
	--no-install-recommends \
			software-properties-common \
			man \
            cmake \
            ctags \
			build-essential \
            htop \
            ca-certificates \
            curl \
            node-less \
			node-clean-css \
			libpq-dev \
			libjpeg-dev \
            libcurl3-dev \
			libxml2-dev \
			libxslt1-dev \
			libffi-dev \
            tmux \
            libfreetype6-dev \
            libpng-dev \
            libjpeg-dev \
            automake \
            pkg-config \
            libpcre3-dev \
            zlib1g-dev \
            liblzma-dev \
            make \
            ssh \
            mc \
            libxml2-utils \
            libxrender1 \
            libxext6 \
            libfontconfig \
            htop \
            rsync \
            vim \
            psmisc \
            lsof \
            git \
            tig \
            sudo \
            less \
            freetds-dev \
            libsasl2-dev \
			libldap2-dev \
			libssl-dev \
            wget \
            cifs-utils \
            imagemagick \
            cups \
            libreoffice \
            libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
            locales \
			libmagickwand-dev \
            ffmpeg \
            zip \
            gpg-agent \
            python3-pip \
            python3-setuptools \
            python3-dev \
            pdftk

RUN \
locale-gen en_US.UTF-8 && \
update-locale && \
echo 'LC_ALL=en_US.UTF-8' >> /etc/environment && \
echo 'LANG=en_US.UTF-8' >> /etc/environment && \
echo 'LANGUAGE=en_US.UTF-8' >> /etc/environment 

ADD liberation-sans /usr/share/fonts/
# rebuild font cache
RUN fc-cache -f -v

# Install nodejs and npm
RUN apt install -y nodejs yarn

# libreoffice
#RUN apt-get update && \
#apt install -q -y libreoffice libreoffice-writer ure libreoffice-java-common libreoffice-core libreoffice-common openjdk-8-jre fonts-opensymbol hyphen-fr hyphen-de hyphen-en-us hyphen-it hyphen-ru fonts-dejavu fonts-dejavu-core fonts-dejavu-extra fonts-droid-fallback fonts-dustin fonts-f500 fonts-fanwood fonts-freefont-ttf fonts-liberation fonts-lmodern fonts-lyx fonts-sil-gentium fonts-texgyre fonts-tlwg-purisa && \
#apt -y -q remove libreoffice-gnome

WORKDIR /tmp

RUN curl -o wkhtmltox.tar.xz -SL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz \
        && echo '3f923f425d345940089e44c1466f6408b9619562 wkhtmltox.tar.xz' | sha1sum -c - \
        && tar xvf wkhtmltox.tar.xz \
        && cp wkhtmltox/lib/* /usr/local/lib/ \
        && cp wkhtmltox/bin/* /usr/local/bin/ \
        && cp -r wkhtmltox/share/man/man1 /usr/local/share/man/


RUN update-alternatives --install /usr/bin/node node /usr/bin/nodejs 10 && \
useradd -ms /bin/bash odoo
RUN \
chown odoo:odoo /home/odoo -R && \
rm -Rf /usr/local/man && mkdir -p /usr/local/man/man1
RUN apt install -y libpython2-dev python2 python-dev python-lxml python-magic
RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
RUN python get-pip.py
RUN pip install pip --upgrade
RUN pip install cython -U

RUN \
	pip install requests[security] && \
	pip install glob2 && \
	pip install pip==9.0.3 --upgrade
RUN pip install lxml psycopg2-binary click pudb psutil

ADD config/$ODOO_VERSION/requirements.txt /root/requirements.txt
RUN pip install pathlib2
RUN pip install -r /root/requirements.txt
#RUN pip install pip==20 -U

# python2 binary error on ubuntu 18.04
# https://github.com/psycopg/psycopg2-wheels/issues/2
RUN mv /bin/sh /bin/sh.bak; ln -s /bin/bash /bin/sh
RUN pip install --no-binary psycopg2
RUN rm /bin/sh; mv /bin/sh.bak /bin/sh


RUN apt update
RUN apt install -y python3-pip
ADD config/${ODOO_VERSION}/pip3 /usr/local/bin/pip3
RUN chmod a+x /usr/local/bin/pip3
RUN pip3 install humanize retrying click pyyaml requests passlib arrow inquirer tabulate psutil iscompatible lxml psycopg2 pudb docker gitpython


WORKDIR /opt

ENV PYTHONIOENCODING=utf8

RUN pip install pudb ipython docker gitpython
RUN echo "\nimport sys; sys.setdefaultencoding('utf-8')" >> /etc/python2.7/sitecustomize.py
RUN python3 -mpip install wodoo
RUN pip install gevent==1.2.2