ARG TARGETARCH
ARG BASE_IMAGE=debian:bullseye
ARG ODOO_VERSION
ARG ODOO_REQUIREMENTS
ARG ODOO_DEB_REQUIREMENTS
ARG ODOO_INSTALL_LIBPOSTAL
ARG ODOO_PYTHON_VERSION
ARG CUSTOMS_SHA

# --------------------------------------------------------------------
# COMPILE LIBPOSTAL
# --------------------------------------------------------------------
FROM $BASE_IMAGE AS libpostal_builder
ARG TARGETARCH
ARG ODOO_INSTALL_LIBPOSTAL
COPY install_libpostal.sh install_libpostal.sh
RUN bash install_libpostal.sh

# --------------------------------------------------------------------
# COMPILE PYTHON
# --------------------------------------------------------------------
FROM $BASE_IMAGE as python_builder
ARG ODOO_PYTHON_VERSION
ADD python/Python-${ODOO_PYTHON_VERSION}.tgz /usr/local/src/python
WORKDIR /usr/local/src/python/Python-${ODOO_PYTHON_VERSION}

RUN apt update && \
apt install -y \
    software-properties-common \
    cmake \
    exuberant-ctags \
    build-essential \
    zlib1g-dev \
    make \
    libssl-dev \
    libffi-dev \
    libsqlite3-dev  \
    libjpeg-dev \
    libcurl3-dev \
    libxml2-dev \
    libxslt1-dev \
    libfreetype6-dev \
    libpng-dev \
    libpcre3-dev \
    liblzma-dev \
    freetds-dev \
    libbz2-dev \
    ncurses-dev

RUN ./configure --enable-optimizations && make -j4 && make install

RUN apt install -y rsync
RUN rsync /usr/local/src/python/Python-${ODOO_PYTHON_VERSION}/ /python -ar


# --------------------------------------------------------------------
# PYTHON PIP PACKAGES
# --------------------------------------------------------------------
FROM $BASE_IMAGE AS build_pip
ARG ODOO_DEB_REQUIREMENTS
ARG ODOO_REQUIREMENTS
ARG ODOO_FRAMEWORK_REQUIREMENTS

ENV VIRTUAL_ENV=/opt/venv/env
ENV PATH="/opt/venv/bin:$PATH"

RUN apt update && apt install -y \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libcups2-dev \
    libpq-dev \
    libsasl2-dev \
    libpython3-dev \
    libldap2-dev \
    libssl-dev \
    libpoppler-cpp-dev \
    freetds-dev \
    pkg-config \
    libfreetype6-dev \
    libffi-dev

# install python from compiled binaries
COPY --from=python_builder /python /opt/python
WORKDIR /opt/python
RUN make install
RUN python3 -mpip install pip --upgrade
RUN /usr/local/bin/python3 -m venv --copies /opt/venv


RUN \
/opt/venv/bin/python3 -mpip install pip -U && \
/opt/venv/bin/python3 -mpip install setuptools==57.5.0 -U
RUN /opt/venv/bin/python3 -mpip install cython==3.0.a9
RUN /opt/venv/bin/python3 -mpip install wheel


RUN echo "$ODOO_DEB_REQUIREMENTS"  | base64 --decode > /root/deb_requirements.txt
RUN xargs apt install < /root/deb_requirements.txt

RUN echo "$ODOO_REQUIREMENTS"  | base64 --decode > /root/pip_requirements.txt
RUN cat /root/pip_requirements.txt | grep -v postal > /root/pip_requirements.filtered.txt
RUN . /opt/venv/bin/activate && /opt/venv/bin/python3 -mpip install -r /root/pip_requirements.filtered.txt

RUN echo "$ODOO_FRAMEWORK_REQUIREMENTS"  | base64 --decode > /root/framework_requirements.txt
RUN /opt/venv/bin/python3 -mpip install -r /root/framework_requirements.txt

RUN /opt/venv/bin/python3 -mpip install pudb ipython marabunta wodoo debugpy

ADD patches/python_3.8.email.patch /usr/local/src
RUN bash /usr/local/src/python_3.8.email.patch

# Openupgradelib
RUN apt install -y git
RUN git clone https://github.com/OCA/openupgradelib /opt/openupgradelib
WORKDIR /opt/openupgradelib
RUN /opt/venv/bin/python3 -mpip install /opt/openupgradelib



# --------------------------------------------------------------------
# ODOO
# --------------------------------------------------------------------
FROM $BASE_IMAGE
ARG TARGETARCH
ARG ODOO_VERSION
ARG ODOO_REQUIREMENTS
ARG ODOO_DEB_REQUIREMENTS
ARG ODOO_INSTALL_LIBPOSTAL
ARG CUSTOMS_SHA

MAINTAINER marc@itewimmer.de

ADD bin/check_sha.sh /usr/local/bin
RUN /bin/bash /usr/local/bin/check_sha.sh "$CUSTOMS_SHA"

# used at a customer to fix proxy; can destroy public keys so no update works
ADD etc/apt/apt.conf.d/99fixbadproxy /etc/apt/apt.conf.d/99fixbadproxy

ENV LANG C.UTF-8
RUN apt update && apt-get install \
	-y \
	--no-install-recommends \
			man \
            exuberant-ctags \
            libtool \
            htop \
            ca-certificates \
            curl \
            node-less \
			node-clean-css \
            ssh \
            libxml2-utils \
            libxrender1 \
            libxext6 \
            libfontconfig \
            rsync \
            vim \
            psmisc \
            git \
            sudo \
            less \
            freetds-dev \
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
            gir1.2-gtk-3.0 \
            libmagickwand-dev \
            libmagic-dev \
            libcups2-dev \
            python3-pip \
            python3-dev \
            python3 \
            locales-all \
            postgresql-client \
            sassc \
            libsqlite3-dev \
            autoconf \
            pkg-config \
            curl \
            time \
            libpoppler-cpp-dev \
            libncurses5 \
            libncurses5-dev \
            libncursesw5 \
            libgeos-dev \
            xfonts-75dpi \
            xfonts-base

ADD liberation-sans /usr/share/fonts/
# rebuild font cache
RUN fc-cache -f -v

# WKHTML2PDF
WORKDIR /tmp
RUN if [ "$TARGETARCH" = "amd64" ]; then \
    curl -o /root/wkhtmltox.deb -sSL  https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    apt-get install -y --no-install-recommends /root/wkhtmltox.deb && \
    rm -rf /var/lib/apt/lists/* /root/wkhtmltox.deb; \
fi
RUN if [ "$TARGETARCH" = "arm64" ]; then \
    curl -o /root/wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_arm64.deb &&  \
    apt-get install -y --no-install-recommends /root/wkhtmltox.deb && \
    rm -rf /var/lib/apt/lists/* /root/wkhtmltox.deb;  \
fi

# Node-JS
RUN update-alternatives --install /usr/bin/node node /usr/bin/nodejs 10 && \
useradd -ms /bin/bash odoo
RUN \
chown odoo:odoo /home/odoo -R && \
rm -Rf /usr/local/man && mkdir -p /usr/local/man/man1




# Transfer python
ENV VIRTUAL_ENV=/opt/venv/env
ENV PATH="/odoolib:/opt/venv/bin:$PATH"
RUN rm -Rf /opt/venv
COPY --from=build_pip /opt/python /opt/python
COPY --from=build_pip /opt/venv /opt/venv
WORKDIR /opt/python
RUN make install
RUN rm /usr/local/bin/python3 /usr/bin/python3

COPY --from=libpostal_builder /usr/local/src /tmp/postal
RUN if [ "$ODOO_INSTALL_LIBPOSTAL" = "1" ]; then \
set -ex && \
mkdir -p /usr/local/src/postal && \
mv /tmp/postal/postal/code /usr/local/src/postal/code && \
mv /tmp/postal/postal/data /usr/local/src/postal/data && \
cd /usr/local/src/postal/code && \
make install && \
ldconfig; \
fi
RUN rm -Rf /tmp/postal
RUN if [ "$ODOO_INSTALL_LIBPOSTAL" = "1" ]; then python3 -mpip install postal; fi

RUN echo "$ODOO_DEB_REQUIREMENTS"  | base64 --decode > /root/deb_requirements.txt
RUN xargs apt install < /root/deb_requirements.txt


WORKDIR /usr/local/bin
RUN ln -s /opt/venv/bin/python3

WORKDIR /opt/odoo

# BUG with M1 and SCRAM authentication
RUN if [ "$TARGETARCH" = "arm64" ]; then \
apt update && \
apt install -y libpq-dev && \
pip3 install psycopg2-binary --no-binary psycopg2-binary --force-reinstall; \
fi
