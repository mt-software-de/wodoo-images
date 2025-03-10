FROM debian:buster
ARG TARGETARCH
ARG ODOO_VERSION
ARG ODOO_INSTALL_LIBPOSTAL
#ARG CUSTOMS_REQUIREMENTS
MAINTAINER marc@itewimmer.de

# used at a customer to fix proxy; can destroy public keys so no update works
ADD etc/apt/apt.conf.d/99fixbadproxy /etc/apt/apt.conf.d/99fixbadproxy

#RUN [[ -z "$CUSTOMS_REQUIREMENTS" && exit -1 ]]
ENV LANG C.UTF-8
RUN apt update --fix-missing && \
apt-get install \
	-y \
	--no-install-recommends \
			software-properties-common \
			man \
            cmake \
            ctags \
			build-essential \
            libtool \
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
            pdftk \
            python3-gi \
            python3-click \
            python3-gi-cairo \
            python3-cairo \
            gir1.2-gtk-3.0 \
            libmagickwand-dev \
            libmagic-dev \
            libcups2-dev \
            python3-pip \
            python3-dev \
            python3 \
            locales-all \
            libpoppler-cpp-dev \
            default-jre \
            libreoffice-java-common \
            postgresql-client \
            git \
            libpq-dev \
            autoconf \
            python-dev \
            pkg-config \
            curl


ADD liberation-sans /usr/share/fonts/
# rebuild font cache
RUN fc-cache -f -v

WORKDIR /tmp

RUN apt install -y xfonts-75dpi xfonts-base libgeos-dev
RUN if [ "$TARGETARCH" = "amd64" ]; then \
    curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.buster_amd64.deb &&  \
    echo 'ea8277df4297afc507c61122f3c349af142f31e5 wkhtmltox.deb' | sha1sum -c - && \
    apt-get install -y --no-install-recommends ./wkhtmltox.deb && \
    rm -rf /var/lib/apt/lists/* wkhtmltox.deb; \
fi
RUN if [ "$TARGETARCH" = "arm64" ]; then \
    curl -o /root/wkhtmltox.deb -sSL  https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_arm64.deb && \
    apt-get install -y --no-install-recommends /root/wkhtmltox.deb && \
    rm -rf /var/lib/apt/lists/* wkhtmltox.deb;  \
fi

RUN update-alternatives --install /usr/bin/node node /usr/bin/nodejs 10 && \
useradd -ms /bin/bash odoo
RUN \
chown odoo:odoo /home/odoo -R && \
rm -Rf /usr/local/man && mkdir -p /usr/local/man/man1

ADD https://raw.githubusercontent.com/odoo/odoo/${ODOO_VERSION}/requirements.txt /root/odoo_requirements.txt
ADD config/$ODOO_VERSION/requirements.txt /root/requirements.txt

#p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3
# PYTHON 3 and PIP
#p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3

#pip3 10.0 is in other directories; hash -r clears the cache of the path
RUN pip3 install wheel
RUN hash -r && \
	pip3 install --upgrade pip && \
	hash -r && \
    pip3 install --upgrade cython
RUN pip3 install 'setuptools<58.0'
RUN pip3 install psycopg2 pyinotify python-magic wand pycups pudb
RUN pip3 install -r /root/odoo_requirements.txt
RUN pip3 install -r /root/requirements.txt
#p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3p3

RUN echo "deb http://ftp.de.debian.org/debian buster main " >> /etc/apt/sources.list.d/dmtx && apt update && apt install -y libdmtx0b
# https://github.com/openvenues/pypostal postal lib for address checking
ADD install_libpostal.sh /root/install_libpostal.sh
RUN if [ "$TARGETARCH" = "amd64" ] && [ "$ODOO_INSTALL_LIBPOSTAL" == "1" ]; then bash /root/install_libpostal.sh; fi


WORKDIR /opt/odoo

RUN python3 -mpip install debugpy docker
RUN pip3 install wodoo
RUN mkdir /opt/venv; ln -s /usr/bin /opt/venv/bin

