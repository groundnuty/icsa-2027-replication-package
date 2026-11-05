# Sandbox image: one image for all options and for the policy gate.
# Build from the repo root:  docker build -f sandbox/Dockerfile -t icsa-sandbox:<tag> . (the tests derive the tag from a hash of the build context)
# python 3.12.13, pinned by digest
FROM python@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

RUN useradd --uid 10001 --create-home --shell /bin/bash agent \
 && mkdir -p /opt/icsa/hooks /opt/icsa/gate /etc/icsa

COPY sandbox/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Instrumentation slot (#9): sitecustomize imports $ICSA_INSTRUMENT_MODULE at
# interpreter start. The default module is a no-op.
COPY sandbox/hooks/ /opt/icsa/hooks/
# Every Python of a traced sandbox loads it, whatever its environment: a .pth line in site-packages (science, #2, 2 Nov 05:44Z).
COPY sandbox/hooks/icsa_site_boot.py /tmp/icsa_site_boot.py
RUN d=$(python -c 'import site; print(site.getsitepackages()[0])') \
 && mv /tmp/icsa_site_boot.py "$d/icsa_site_boot.py" \
 && echo 'import icsa_site_boot' > "$d/icsa_site_boot.pth"
# The policy gate (network enforcement); runs in its own container, never next
# to the agent.
COPY icsa/sandbox/gate.py icsa/sandbox/gatepolicy.py /opt/icsa/gate/

ENV PYTHONPATH=/opt/icsa/hooks \
    ICSA_INSTRUMENT_MODULE=icsa_noop_instrument \
    ICSA_TRACE_DIR=/trace \
    SSL_CERT_FILE=/etc/icsa/ca.pem \
    REQUESTS_CA_BUNDLE=/etc/icsa/ca.pem \
    CURL_CA_BUNDLE=/etc/icsa/ca.pem \
    FSSPEC_CONFIG_DIR=/nonexistent \
    HOME=/work \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1
USER agent
WORKDIR /work
