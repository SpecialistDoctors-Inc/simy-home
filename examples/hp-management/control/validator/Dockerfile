FROM mcr.microsoft.com/playwright/python:v1.64.1-noble@sha256:7d030ac0638b279ecc72493f8b6706fecef80a893679a23b02f912905c4915c0
# Apply available Noble package patches inside this image, never on the host.
# Include vendor-published phased patches; no distro migration or host changes.
RUN apt-get update \
    && apt-get -o APT::Get::Always-Include-Phased-Updates=true upgrade -y --no-install-recommends \
    # The renderer uses Chromium screenshots only, never WebKit/Firefox or video capture.
    && apt-get purge -y --no-install-recommends \
       gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-libav \
       libgstreamer-plugins-bad1.0-0 libopenexr-3-1-30 libfluidsynth3 libcjson1 \
       libavcodec60 libavformat60 libavfilter9 libavutil58 libswscale7 \
       libswresample4 libpostproc57 libass9 libzvbi0t64 libzvbi-common libmbedcrypto7t64 libsrt1.5-gnutls \
    && rm -rf /ms-playwright/firefox-* /ms-playwright/webkit-* /ms-playwright/ffmpeg-* \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/validator-requirements.txt
RUN pip install --no-cache-dir -r /opt/validator-requirements.txt && chmod 1777 /tmp
WORKDIR /opt/validator
COPY render.py smoke.py /opt/validator/
ENV PYTHONDONTWRITEBYTECODE=1 AWS_EC2_METADATA_DISABLED=true HOME=/tmp TMPDIR=/tmp
USER 1000:1000
ENTRYPOINT ["python3", "/opt/validator/render.py"]
VOLUME ["/tmp"]
