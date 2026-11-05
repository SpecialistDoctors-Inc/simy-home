FROM mcr.microsoft.com/playwright/python:v1.56.0-noble@sha256:508b37a524219d210a67a7190beb079efda72553e0dcb9ef21d4dae8f8a7686b
COPY requirements.txt /opt/validator-requirements.txt
RUN pip install --no-cache-dir -r /opt/validator-requirements.txt && chmod 1777 /tmp
WORKDIR /opt/validator
COPY render.py smoke.py /opt/validator/
ENV PYTHONDONTWRITEBYTECODE=1 AWS_EC2_METADATA_DISABLED=true HOME=/tmp TMPDIR=/tmp
USER 1000:1000
ENTRYPOINT ["python3", "/opt/validator/render.py"]
VOLUME ["/tmp"]
